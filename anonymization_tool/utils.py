import hashlib
import numpy as np
import random

def pseudonymize_sha256(value):
    return hashlib.sha256(str(value).encode()).hexdigest()

def pseudonymize_md5(value):
    return hashlib.md5(str(value).encode()).hexdigest()

def pseudonymize_random_string(value, length=8):
    return ''.join(np.random.choice(list('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'), length))

def swap_column_values(df, column):
    original_values = df[column].values
    np.random.shuffle(original_values)
    df[column] = original_values
    return df

def generalize_to_range(value, range_size=10):
    try:
        numeric_value = float(value)
        lower_bound = (numeric_value // range_size) * range_size
        upper_bound = lower_bound + range_size - 1
        return f"{int(lower_bound)}-{int(upper_bound)}"
    except ValueError:
        return value  # If not numeric, return the original value

def create_swap_mapping(values):
    """Creates a swap mapping for the given values, ensuring randomness without pattern repetition."""
    unique_values = np.array(values.dropna().unique())
    shuffled_values = unique_values.copy()
    
    # Shuffle the array until it doesn't match the original
    while np.any(shuffled_values == unique_values):
        np.random.shuffle(shuffled_values)
    
    return dict(zip(unique_values, shuffled_values))



def create_consistent_swap_mapping(column_values):
    """Creates a consistent swap mapping ensuring no value is lost or duplicated."""
    original_values = column_values.dropna().tolist()
    unique_values = list(set(original_values))  # Ensure unique values

    # Shuffle the unique values
    shuffled_values = unique_values[:]
    random.shuffle(shuffled_values)
    
    # Ensure we don't accidentally leave any values in their original position
    for i in range(len(shuffled_values)):
        if unique_values[i] == shuffled_values[i]:
            # Swap with the next element or the first one
            if i < len(shuffled_values) - 1:
                shuffled_values[i], shuffled_values[i+1] = shuffled_values[i+1], shuffled_values[i]
            else:
                shuffled_values[i], shuffled_values[0] = shuffled_values[0], shuffled_values[i]
    
    return dict(zip(unique_values, shuffled_values))


def apply_methods(sheet_df, selected_methods, swap_mappings, random_string_mappings):
    for column in sheet_df.columns:
        method = selected_methods.get(f'method_{column}')
        if method == 'sha256':
            sheet_df[column] = sheet_df[column].apply(pseudonymize_sha256)
        elif method == 'md5':
            sheet_df[column] = sheet_df[column].apply(pseudonymize_md5)
        elif method == 'random_string':
            if column not in random_string_mappings:
                unique_values = sheet_df[column].unique()
                random_string_mappings[column] = {val: pseudonymize_random_string(str(val)) for val in unique_values}
            sheet_df[column] = sheet_df[column].map(random_string_mappings[column])
        elif method == 'swap' and column in swap_mappings:
            sheet_df[column] = sheet_df[column].map(swap_mappings[column])
        elif method == 'generalize':
            range_size = int(selected_methods.get(f'range_size_{column}', 10))
            sheet_df[column] = sheet_df[column].apply(generalize_to_range, args=(range_size,))
    return sheet_df
