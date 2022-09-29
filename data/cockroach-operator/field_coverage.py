import os
import json

class crdb_field_counter():
    def __init__(self, e2e_path: str):
        self.e2e_path = e2e_path
        with open('data/cockroach-operator/all_field_func.csv', 'r') as f:
            self.funcs = {}
            for line in f.readlines():
                self.funcs[line.split(',')[0]] = int(line.split(',')[1])
        
    def count(self) -> list:
        if not os.path.exists(self.e2e_path):
            raise Exception("e2e folder does not exist!")
        fields = {}
        for root, _, files in os.walk(self.e2e_path):
            for file in files:
                if file.endswith('_test.go'):
                    # print(os.path.join(root, file))
                    with open(os.path.join(root, file), 'r') as f:
                        for line in f:
                            for func in self.funcs:
                                if func in line:
                                    if func not in fields:
                                        fields[func] = 1
                                    else:
                                        fields[func] += 1
                    
        with open('data/cockroach-operator/fields.json', 'w') as f:
            json.dump(fields, f, indent=2)
        num_fields = 0
        for field in fields:
            num_fields += self.funcs[field]
        print('The number of fields covered is: ', num_fields)      
        return fields

if __name__ == '__main__':
    cfc = crdb_field_counter('../cockroach-operator/e2e') # Specify the e2e folder path here
    cfc.count()
    
                