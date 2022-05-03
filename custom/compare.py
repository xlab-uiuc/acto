from deepdiff.helper import NotPresent

class CompareMethods:
    def __init__(self):
        # self.method_list = \
        #     [a for a in dir(self) if not a.startswith('__') and a != "compare" and callable(getattr(self, a))] 
        self.custom_operators = []
        pass
    
    # def __iter__(self):
    #     # make the defined methods iterable 
    #     for method in self.method_list:
    #         yield getattr(self, method)

    def operator(self, input, output) -> bool:
        if input == output:
            return True
        elif input == None and isinstance(output, NotPresent):
            return True
        elif isinstance(input, NotPresent) and output == None:
            return True
        elif isinstance(input, NotPresent) and isinstance(output, NotPresent):
            return True
        elif str(input) in str(output):
            return True
        else:
            for op in self.custom_operators:
                if op(input, output):
                    return True
            return False

    def compare(self, in_prev, in_curr, out_prev, out_curr) -> bool:
        # try every compare method possible
        if self.operator(in_prev, out_prev) and self.operator(in_curr, out_curr):
                return True
        else:
            return False
    
if __name__ == '__main__':
    compare = CompareMethods()
    result = compare.compare(NotPresent(), 'asdf', None, 'asdf')
    print(result)