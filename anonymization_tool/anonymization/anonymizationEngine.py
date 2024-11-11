import hashlib
import numpy as np
import random

def pseudonymize_sha256(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def generalize_to_range(value, range_size=10):
    try:
        numeric_value = float(value)
        lower_bound = (numeric_value // range_size) * range_size
        upper_bound = lower_bound + range_size - 1
        return f"{int(lower_bound)}-{int(upper_bound)}"
    except ValueError:
        return value 

def create_swap_mapping(values):

    unique_values = np.array(values.dropna().unique())
    shuffled_values = unique_values.copy()
    
    while np.any(shuffled_values == unique_values):
        np.random.shuffle(shuffled_values)
    
    return dict(zip(unique_values, shuffled_values))



def create_consistent_swap_mapping(column_values):

    original_values = column_values.dropna().tolist()
    unique_values = list(set(original_values))  

    shuffled_values = unique_values[:]
    random.shuffle(shuffled_values)
    
    for i in range(len(shuffled_values)):
        if unique_values[i] == shuffled_values[i]:
            if i < len(shuffled_values) - 1:
                shuffled_values[i], shuffled_values[i+1] = shuffled_values[i+1], shuffled_values[i]
            else:
                shuffled_values[i], shuffled_values[0] = shuffled_values[0], shuffled_values[i]
    
    return dict(zip(unique_values, shuffled_values))
