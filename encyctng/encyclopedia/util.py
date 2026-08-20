import random
import string


def random_string(length=10):
    """Generate a random string of the requested length"""
    return ''.join(
        random.choices(string.ascii_letters + string.digits, k=length)
    )
