import numpy as np

def generic_catagorical_conversion(x, dictionary_str):
    """
    Converts a value using a categorical dictionary.

    Args:
        x (any): The value to convert.
        dictionary_str (str): The dictionary as a string.

    Returns:
        any: The converted value or NaN if conversion fails.
    """
    dictionary_init = eval(dictionary_str)
    dictionary = {str(key): value for key, value in dictionary_init.items()} # convert all keys to string dtype
    x = str(x)
    if x in list(dictionary):
        out = dictionary[x]
        if not out == None:
            return out
        else:
            return np.nan
    else:
        return np.nan

def dtype_conversion(x, dtype):
    """
    Converts a value to a specified data type.

    Args:
        x (any): The value to convert.
        dtype (str): The target data type.

    Returns:
        any: The converted value or NaN if conversion fails.
    """
    try:
        if dtype == 'string':
            return str(x)
        elif dtype == 'str':
            return str(x)    
        elif dtype == 'float':
            return float(x)
        elif dtype == 'integer':
            return int(x)
        elif dtype == 'int':
            return int(x)
        elif dtype == 'boolean':
            return bool(x)
        elif dtype == 'other':
            return x
    except:
        return np.nan

def generic_direct_conversion(x, x_str, source_dtype, target_dtype):
    """
    Performs a direct conversion of a value.

    Args:
        x (any): The value to convert.
        x_str (str): The conversion expression as a string.
        source_dtype (str): The source data type.
        target_dtype (str): The target data type.

    Returns:
        any: The converted value.
    """
    x = dtype_conversion(x, source_dtype)
    x = eval(x_str)
    return dtype_conversion(x, target_dtype)