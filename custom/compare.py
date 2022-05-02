from deepdiff.helper import NotPresent

class CompareMethods:
    def __init__(self):
        self.method_list = \
            [a for a in dir(self) if not a.startswith('__') and a != "compare" and callable(getattr(self, a))] 
    
    def __iter__(self):
        # make the defined methods iterable 
        for method in self.method_list:
            yield getattr(self, method)

    def compare(self, in_prev, in_curr, out_prev, out_curr) -> bool:
        # try every compare method possible
        if in_prev == None or isinstance(in_prev, NotPresent):
            # if prev value is null or NotPresent, we only compare the current value
            # because operator could use default value
            for method in self:
                if method(in_prev, in_curr, out_prev, out_curr):
                    return True
        else:
            for method in self:
                if method(in_prev, in_curr, out_prev, out_curr):
                    return True
        return False 

    # add custom compare methods below

    def compare_basic(self, in_prev, in_curr, out_prev, out_curr) -> bool:
        if in_prev in out_prev and in_curr in out_curr:
            return True
        return False

    def compare_number_and_string(self, in_prev, in_curr, out_prev, out_curr) -> bool:
        in_prev = str(in_prev)
        in_curr = str(in_curr)
        out_prev = str(out_prev)
        out_curr = str(out_curr)
        
        return self.compare_basic(in_prev, in_curr, out_prev, out_curr)
    