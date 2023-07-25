'''Helper functions for experiment management scripts.'''

import os, sys, subprocess
import functools as ft
from typing import Any, Callable, Optional, TypeAlias, Union
from termcolor import cprint

from typing import List
from subprocess import CompletedProcess
from os import PathLike

Predicate : TypeAlias = Callable[[Any],bool]
StrOrBytesPath : TypeAlias = type[str] | type[bytes] | type[PathLike[str]] | type[PathLike[bytes]]
FileDescriptorOrPath : TypeAlias = type[int] | type[str] | type[bytes] | type[PathLike[str]] | type[PathLike[bytes]]

########################################################################################################################

def downwardlab_home(path:Optional[StrOrBytesPath]=os.getcwd()):
    '''Search CWD and direct ancestors for directory that has 'downward' and VAL subdirectories.
    
    Directory Name              Description                     Additional Check
    downward :                  Fast Downward algo repo         Contains 'fast-downward.py' file
    VAL :                       VAL plan validation repo        Contains 'validate' file
    '''
    def condition(path):
        landmark_dirs = {
            'downward' : os.path.join(path, 'downward'),
            'val' : os.path.join(path, 'VAL')
        }
        landmark_files = {
            'fastdownward' : os.path.join(landmark_dirs['downward'], 'fast-downward.py'),
            'validate' : os.path.join(landmark_dirs['val'], 'validate')
        }
        return (    all(os.path.exists(d) for d in landmark_dirs.values()) and
                    all(os.path.exists(f) and not os.path.isdir(f) for f in landmark_files.values())    )
        
    path = os.path.abspath(path)
    if condition(path): return path
    return path if condition(path) else get_nearest_ancestor(path,condition=condition)



def get_nearest_ancestor(path:Optional[StrOrBytesPath]=None, 
                         condition:Optional[Predicate]=None
                         ) -> StrOrBytesPath | None:
    '''Find path of first ancestor for which condition is satisfied.'''
    path = os.path.abspath(path) if path else os.getcwd()
    # if no condition specified, return nearest ancestor unconditionally
    if condition is None:
        condition = lambda d: True

    def check_parent(path, condition):
        parent = os.path.dirname(path)
        # recognize if we've encountered a top-level or nonexistent path
        if (parent==path) or (not os.path.exists(parent)):
            return None
        # if parent satisfies condition, it is the nearest ancestor
        elif condition(parent):
            return parent
        # otherwise, go up another level
        else:
            return check_parent(parent, condition)

    ancestor = check_parent(path, condition)
    if ancestor is None: 
        raise FileNotFoundError(f"DownwardLab Home directory could not be found in direct ancestors of path '{path}'.")
    return ancestor


def chmod_plus_x(path:StrOrBytesPath):
    # Reference: https://stackoverflow.com/questions/12791997/how-do-you-do-a-simple-chmod-x-from-within-python/55591471#55591471
    import os, stat
    def get_umask():
        umask = os.umask(0)
        os.umask(umask)
        return umask
    mode = os.stat(path).st_mode
    exec_mask = (  stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH )
    os.chmod(path, mode | ( exec_mask & ~get_umask() ))


def add_abort_condition(rval_condition:Predicate, error:Union[bool,type]=False, verbose:bool=False, errmsg:str='default'):
    '''Decorator that aborts process if the decorated function returns a value that satisfies rval_condition.

    TODO: add logging
    '''
    def decorator(f:Callable):
        @ft.wraps(f)
        def wrapper(*args, **kwargs):
            rval = f(*args, **kwargs)
            if rval_condition(rval):    abort(rval)
            else:                       return rval     
        def abort(rval:Any):
            msg = format_error_msg(errmsg, rval)
            if verbose:   
                cprint(f"[ABORT] {msg}", "red")
            if error:
                if issubclass(error):   raise error(msg)
                else:                   raise Exception(msg, rval_condition, f, rval) 
            else:
                sys.exit(1)
        def format_error_msg(msg, rval):
            if msg is True or errmsg=='default': 
                msg = f"function '{f.__name__}' return value '{rval}' meets abort condition."
            elif not msg: 
                msg = ''
            return msg
        return wrapper
    return decorator




class VirtualenvwrapperCLI:

    _SOURCE_CMD = 'source "${VIRTUALENVWRAPPER_SCRIPT}"'

    ####################### Virtualenv API #######################
    
    @classmethod
    def mkvirtualenv(cls, env_name:str,
                     projectpath:Optional[StrOrBytesPath]=None, 
                     install:Optional[Union[str,List[str],FileDescriptorOrPath]]=None
                    ) -> CompletedProcess[bytes]:
        
        options = cls._OptionsHandler.mkvirtualenv_options(projectpath, install)
        return VirtualenvwrapperCLI.exec(f'mkvirtualenv {options} {env_name}')
    
    def rmvirtualenv(env_name:str) -> CompletedProcess[bytes]:
        return VirtualenvwrapperCLI.exec(f'rmvirtualenv {env_name}')
    
    def workon(env_name:str='') -> CompletedProcess[bytes]:
        return VirtualenvwrapperCLI.exec(f'workon {env_name}')
    
    #####################################################################
    
    # wrapper for '_exec_with_virtualenvwrapper_api' for ease of use
    def exec(*commands:List[str]) -> CompletedProcess[bytes]:
        return VirtualenvwrapperCLI._exec_with_virtualenvwrapper_api(*commands)

    def _exec_with_virtualenvwrapper_api(*commands:str, 
                                         executable:StrOrBytesPath='/bin/bash', 
                                         check:bool=True
                                         ) -> CompletedProcess[bytes]:
        commands = [VirtualenvwrapperCLI._SOURCE_CMD] + list(commands)
        CMD = " ; ".join(commands)
        return subprocess.run(CMD, shell=True, executable=executable, check=check)
    
    def _is_requirements_file(file:FileDescriptorOrPath):
        return os.path.exists(file) and os.path.basename(file)=='requirements.txt'

    class _OptionsHandler:
        def _option_string(options:dict):
            join = lambda strlist,delim=" ": delim.join(strlist)
            options_list = [
                f" {flag} {args}" if isinstance(args, str) else join([f" {flag} {arg}" for arg in args])
                for flag, *args in options.items()
            ]
            return join(options_list)
        
        @classmethod
        def mkvirtualenv_options(cls, 
                                 projectpath:Optional[StrOrBytesPath]=None, 
                                 install:Optional[Union[str,List[str],FileDescriptorOrPath]]=None
                                ) -> str:
            options = {}
            if projectpath is not None:
                options['-a'] = projectpath 
            if install is not None:
                if VirtualenvwrapperCLI._is_requirements_file(install): options['-r'] = install 
                elif isinstance(install, str):                          options['-i'] = [install]
                else:                                                   options['-i'] = install
            return cls._option_string(options)
        



            


########################################################################################################################
def main():
    '''Testing
    '''
    out = downwardlab_home()
    print(out)


if __name__ == "__main__":
    main()