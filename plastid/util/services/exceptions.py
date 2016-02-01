#!/usr/bin/env python
"""This module contains custom exception and warning classes, as well as 
an implementation of a custom warning filter action, called `"onceperfamily"`.

The `onceperfamily` action
--------------------------
This filter action groups warning messages by families specified regular expressions,
and only prints the first instance of a warning for each family. In contrast,
Python's `"once"` action prints any warning string once, even if the strings
match the same regex in the same warnings filter.

To use this action, use the following two functions:

  - :func:`filterwarnings` to create the warnings filter. Because :func:`filterwarnings`
    wraps Python's :func:`warnings.filterwarnings`, it may be used as a drop-in
    replacement. for creation of any warnings filter.
    
  - :func:`warn` or :func:`warn_explicit`. Again, these are drop-in replacements
    for Python's :func:`warnings.warn` and :func:`warnings.warn_explicit` that
    additionally check the `onceperfamily` filters.


Exceptions
----------
|MalformedFileError|
    Raised when a file cannot be parsed as expected, and
    execution must halt

Warnings
--------
|ArgumentWarning|
    Warning for command-line arguments that:
    
      - are nonsenical, but recoverable
      - together might cause very slow execution
        (e.g. run would be optimized by other combinations)

|FileFormatWarning|
    Warning for slightly malformed but usable files

|DataWarning|
    Warning raised when:

      - data has unexpected attributes
      - data has nonsensical, but recoverable values for attributes
      - when values are out of the domain of a given operation,
        but skipping the operation or estimating the value is permissible


See also
--------
warnings
    Warnings module
"""
import re
import warnings
import inspect

#===============================================================================
# INDEX: Warning and exception classes
#===============================================================================

class MalformedFileError(Exception):
    """Exception class for when files cannot be parsed as they should be
    """
    
    def __init__(self,filename,message,line_num=None):
        """Create a |MalformedFileError|
        
        Parameters
        ----------
        filename : str
            Name of file causing problem
        
        message : str
            Message explaining how the file is malformed.
        
        line_num : int or None, optional
            Number of line causing problems
        """
        self.filename = filename
        self.msg      = message
        self.line_num = line_num
    
    def __str__(self):
        if self.line is None:
            return "Error opening file '%s': %s" % (self.filename, self.msg)
        else:
            return "Error opening file '%s' at line %s: %s" % (self.filename, self.line_num, self.msg)



class ArgumentWarning(Warning):
    """Warning for nonsensical but recoverable combinations of command-line arguments,
    or arguments that risk slow program execution"""
    pass


class FileFormatWarning(Warning):
    """Warning for slightly malformed but usable files"""
    pass


class DataWarning(Warning):
    """Warning for unexpected attributes of data.
    Raised when:

      - data has unexpected attributes
      - data has nonsensical, but recoverable values
      - values are out of the domain of a given operation, but execution
        can continue if the value is estimated or the operation skipped
    """



#===============================================================================
# INDEX: Plastid's extensions to Python warnings
#===============================================================================

pl_once_registry = {}
"""Registry of `onceperfamily` warnings that have been seen in the current execution context"""

pl_filters       = []
"""Plastid's own warnings filters, which allow additional actions compared to Python's"""

def filterwarnings(action,message="",category=Warning,module="",lineno=0,append=0):
    """Insert an entry into the warnings filter. Behaviors are as in :func:`warnings.filterwarnings`,
    except the additional action `'onceperfamily'` can be used to allow one warning per `family`
    of messages, specified by a regex. 
    
    This allows individual warnings to give more detailed information, without each being
    regarded as its own warning by Python's warning system (the defualt behavior of `'once'`).
    
    
    Parameters
    ----------
    action : str
        How the warning should be filtered. Accceptable values are "error",
        "ignore", "always", "default", 'module", "once", and "onceperfamily"
        
    message : str, optional
        str that can be compiled to a regex, used to detect warnings. If "onceperfamily"
        is chosen, only the first warning to give a string that matches the regex
        will be shown. For other actions, behaviors are as described in :mod:`warnings`.
        (Default: `""`, match any message)
        
    category : Warning or subclass, optional
        Type of warning. (Default: :class:`Warning`)

    module : str, optional
        str that can be compiled to a regex, limiting the warning behavior to modules
        that match that regex. (Default: `""`, match all modules)
        
    lineno : int, optional
        integer line used to specify warning in source code. If 0 (default), match
        all warnings regardless of line number.
        
    append : int, optional
        If 1, add warning to end of filter list. If 0 (default), insert warning at 
        beginning of filters list.
        
    
    See also
    --------
    warnings.filterwarnings
        Python's warnings filter
    """
    tup = (action,re.compile(message,re.I),category,re.compile(module),lineno)
    if action == "onceperfamily":
        if append == 1:
            pl_filters.append(tup)
        else:
            pl_filters.insert(0,tup)
    else:
        warnings.filterwarnings(action,message=message,
                                category=category,module=module,
                                lineno=lineno,append=append)

def warn(message,category=None,stacklevel=1):
    """Issue a non-essential warning to users, allowing `plastid`-specific warnings filters
    
    Parameters
    ----------
    message : str
        Message
    
    category: :class:`Warning`, or subclass, optional
        Type of warning
        
    stacklevel : int
        Ignored
        
    See also
    --------
    plastid.util.services.exceptions.filterwarnings
        plastid-specific warnings filters
    
    warnings.warn
        Python's warning system, which this wraps
    """
    if category is None:
        category = UserWarning
        
    _, filename, lineno, _, _, _ = inspect.stack()[stacklevel]
    warn_explicit(message,category,filename,lineno,module=filename)

def warn_explicit(message,category,filename,lineno,module=None,registry=None,module_globals=None):
    """Low-level interface to issue warnings, allowing `plastid`-specific warnings filters

    Parameters
    ----------
    message : str
        Message
    
    category: :class:`Warning`, or subclass, optional
        Type of warning

    filename : str
        Name of module from which warning is issued
    
    lineno : int, optional
        Line in module at which warning is called

    module : str, optional
        Module name
    
    registry : dict, optional
        Registry of ignore filters (see source code for :func:`warnings.warn_explicit`
    
    module_globals : dict, optional
        Dictionary of module-level variables
        
    
    See also
    --------
    plastid.util.services.exceptions.filterwarnings
        plastid-specific warnings filters

    warnings.warn_explicit
        Python's warning system, which this wraps
    """
    global pl_once_registry
    for _, pat, filter_category, mod, filter_line in pl_filters:
        if pat.match(message) and issubclass(category,filter_category) and\
           (module is None or mod.match(module)) and\
           (filter_line == 0 or filter_line == lineno):
            
            tup =(pat.pattern,filter_category,mod,filter_line) 
            if tup in pl_once_registry:
                return
            else:
                print "adding to registry"
                pl_once_registry[tup] = 1
                break
            
    warnings.warn_explicit(message,category,filename,lineno,
                           module=module,registry=registry,
                           module_globals=module_globals)
