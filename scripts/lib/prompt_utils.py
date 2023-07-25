from typing import Any, Collection, Optional, TypeAlias
from dataclasses import dataclass
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import FormattedText

# Type Aliases
Style : TypeAlias = type[dict] | type["PyPromptTextAttrs"]
Text  : TypeAlias = type[str]  | type["PyPromptFormattedText"] | type[FormattedText]

########################################################################################################################

'''Toggle whether code under 'if __name__=="__main__":' should execute when run as script.'''
RUNNABLE = False

########################################################################################################################

@dataclass
class PyPromptTextAttrs:
    color     : Optional[str]  = None
    bgcolor   : Optional[str]  = None
    bold      : Optional[bool] = None
    italic    : Optional[bool] = None
    underline : Optional[bool] = None
    strike    : Optional[bool] = None
    blink     : Optional[bool] = None
    reverse   : Optional[bool] = None
    hidden    : Optional[bool] = None
    
    def to_dict(self) -> dict :
        return self.__dict__
    
    @staticmethod
    def from_dict(d:dict) -> "PyPromptTextAttrs" :
        return PyPromptTextAttrs(**d)

    def to_style_str(self) -> str:
        tokenize    = lambda s: str(s).strip() if not None else ''
        add_prefix  = lambda prfx: lambda val: f"{tokenize(prfx)}{tokenize(val)}"
        toggle_attr = lambda attr: lambda val: f"{'no' if val is False else ''}{tokenize(attr)}"
        attr_formatter = {
              'color'     : tokenize
            , 'bgcolor'   : add_prefix('bg:')
            , 'bold'      : toggle_attr('bold')
            , 'italic'    : toggle_attr('italic')
            , 'underline' : toggle_attr('underline')
            , 'strike'    : toggle_attr('strike')
            , 'blink'     : toggle_attr('blink')
            , 'reverse'   : toggle_attr('reverse')
            , 'hidden'    : toggle_attr('hidden')
        }
        return " ".join([attr_formatter[k](v) for k,v in self.to_dict().items() if v is not None ])
    
    def __str__(self) -> str:
        classname = type(self).__name__
        attrlist = ', '.join([f'{attr}={val}' for attr,val in self.to_dict().items() if val is not None])
        return f'{classname}({attrlist})'
    


class PyPromptFormattedText():
    
    def __init__(self, text:str, style:Optional[Style]=None, **style_kwargs:dict[str,Any]) -> None:
        self.text = text
        # Raise error if style is overdefined
        if style is not None and not style_kwargs=={}:
            raise ValueError("too many arguments specified (expected at most one of 'style' and 'style_kwargs')")
        
        if isinstance(style, PyPromptTextAttrs):
            self.style = style
        elif isinstance(style, dict):
            self.style = PyPromptTextAttrs.from_dict(style)
        elif style is None:
            self.style = PyPromptTextAttrs(**style_kwargs)
        else:
            raise TypeError("Inappropriate argument type for parameter 'style' (expected one of 'None', 'dict', or 'PyPromptTextAttrs')")

    class style_property(property):
        @staticmethod
        def __fget_textattr(attr:str) -> Any:
            return lambda self: getattr(self.style, attr)
        @staticmethod
        def __fset_textattr(attr:str) -> None:
            return lambda self,val: setattr(self.style, attr, val)
        def __init__(self,attr:str) -> None:
            super().__init__(self.__fget_textattr(attr), self.__fset_textattr(attr))

    text: str
    style: PyPromptTextAttrs = None
    color     : Optional[str] = style_property("color")
    bgcolor   : Optional[str] = style_property("bgcolor")
    bold      : Optional[bool] = style_property("bold")
    italic    : Optional[bool] = style_property("italic")
    underline : Optional[bool] = style_property("underline")
    strike    : Optional[bool] = style_property("strike")
    blink     : Optional[bool] = style_property("blink")
    reverse   : Optional[bool] = style_property("reverse")
    hidden    : Optional[bool] = style_property("hidden")
    style_str : str = property(fget=lambda self: self.style.to_style_str() if self.style is not None else '')

    
    def to_dict(self) -> dict[str, Any]:
        return self.__dict__

    def to_formatted_text(self) -> FormattedText:
        return FormattedText([(self.style_str, self.text)])
    
    def __str__(self) -> str:
        return str(self.text)
    
    def __repr__(self) -> str:
        classname = type(self).__name__
        return f'{classname}(text="{self.text}", style={self.style})'
    
    

class Prompt(PyPromptFormattedText):
    def __init__(self, text:str, style:Optional[Style]=None, **style_kwargs:dict[str,Any]):
        text = text if text.endswith(' ') else text+' '
        super().__init__(text, style, **style_kwargs)
    
    def __call__(self, format=True) -> str:
        if format: return prompt(self.to_formatted_text())
        else:      return input(self.text)

    


class ConfirmationPrompt():

    @dataclass
    class _ResponseHandling:
        affirmative:Collection[str]
        negative:Collection[str]
        case_sensitive:bool

        @property
        def valid(self) -> Collection[str]:
            return set([*self.affirmative, *self.negative])

        def check_element(self, elem:str, collection:Collection[str]):
            e = elem.lower() if self.case_sensitive is False else elem
            C = [c.lower() for c in collection] if self.case_sensitive is False else collection
            return e in C
        def is_valid(self, response:str) -> bool:
            return self.check_element(response, self.valid)
        def is_affirmative(self, response:str) -> bool:
            return self.check_element(response, self.affirmative)
        def is_negative(self, response:str) -> bool:
            return self.check_element(response, self.negative)


    def __init__(self,  prompt:str, *,
                        style:Optional[Style]=None,
                        max_attempts:Optional[int]=None,
                        invalid_response_warning:Text="Invalid response.",
                        max_attempts_err:Text="Maximum attempts exceeded.",
                        warning_style:Optional[Style]=None,
                        error_style:Optional[Style]=None,
                        affirmative:Collection[str]=("y","yes"),
                        negative:Collection[str]=("n","no"), # todo: make these able to accept boolean predicates
                        case_sensitive:bool=False,
                        **style_kwargs:dict[str,Any]
                        ):
        
        self.prompt = Prompt(text=prompt, style=style, **style_kwargs)
        self.max_attempts = max_attempts
        self._responses = self._ResponseHandling(affirmative=affirmative, negative=negative, case_sensitive=case_sensitive)
        self._exceptions = {
            "InvalidInput" : PyPromptFormattedText(text=invalid_response_warning, style=warning_style),
            "MaxAttempts"  : PyPromptFormattedText(text=max_attempts_err, style=error_style)
        }



    def __call__(self) -> Optional[bool]:
        attempt = 1
        while True:
            response = self.prompt()
            if self._responses.is_valid(response):
                # Valid input; return True if affirmative, or False if negative
                return self._responses.is_affirmative(response)
            
            # Invalid input; repeat prompt
            print_formatted_text(self._exceptions["InvalidInput"].to_formatted_text())
            attempt+=1

            try: # Assert that maximum number of attempts has not been exceeded
                assert self.max_attempts is None or attempt <= self.max_attempts, "exceeded input attempt limit"
            except AssertionError as e:
                # Too many failed attempts; print error message and throw AssertionError
                print_formatted_text(self._exceptions["MaxAttempts"].to_formatted_text())
                raise e
        

    def __str__(self) -> bool:
        clsname = type(self).__name__
        return f"{clsname}('{self.prompt}')"

    def __repr__(self) -> bool:
        clsname = type(self).__name__
        attrs = [(attr,val if not isinstance(val,str) else f"'{val}'") for attr,val in self.__dict__.items()]
        return f'{clsname}(' + ', '.join([f'{attr}={val}' for attr,val in attrs]) + ')'
    
        
def confirmation_prompt(prompt:str, *,
                        style:Optional[Style]=None,
                        max_attempts:Optional[int]=None,
                        invalid_response_warning:Text="Invalid response.",
                        max_attempts_err:Text="Maximum attempts exceeded.",
                        warning_style:Optional[Style]=None,
                        error_style:Optional[Style]=None,
                        affirmative:Collection[str]=("y","yes"),
                        negative:Collection[str]=("n","no"), # todo: make these able to accept boolean predicates
                        case_sensitive=False,
                        **style_kwargs
                        ) -> str:
    '''Create an anonymous confirmation prompt and call it immediately, returning the result.
    '''
    return ConfirmationPrompt(prompt=prompt,
                                style=style,
                                max_attempts=max_attempts,
                                invalid_response_warning=invalid_response_warning,
                                max_attempts_err=max_attempts_err,
                                warning_style=warning_style,
                                error_style=error_style,
                                affirmative=affirmative,
                                negative=negative,
                                case_sensitive=case_sensitive,
                                **style_kwargs
    ).__call__()


################################################## TEST SCRIPT #########################################################

def test():
    expdir = "{expdir}"
    experiment_name = "{experiment_name}"
    OVERWRITE_WARNING = FormattedText([
        ("#ff0000 bold", "[WARNING] "),
        ("#ffff00", f"Experiment directory {expdir} already exists. Creating a new experiment of this name will "),
        ("#ff0000 underline bold", f"permanently delete"),
        ("#ffff00", f" all existing files in {expdir} and "),
        ("#ff0000 bold underline", f"completely reset"),
        ("#ffff00", f" the '{experiment_name}' virtualenv."),
    ])
    PROMPT = ConfirmationPrompt(
        prompt=f"\nAre you sure you want to continue with overwriting? ('yes'/'no') ",
        color="#ff0000",
        bold=True,
        invalid_response_warning="Please input 'yes' or 'no.'",
        max_attempts=2
    )

    print_formatted_text(OVERWRITE_WARNING)
    response = PROMPT()



if __name__=="__main__":
    if RUNNABLE: test()