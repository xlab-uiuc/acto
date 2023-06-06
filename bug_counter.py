class BugCounter():
    def __init__(self):
        self.num_bugs = 0
        self.num_confirmed = 0
        self.num_fixed = 0
        self.num_by_bugs = 0
        self.num_by_confirmed = 0
        self.num_by_fixed = 0
        self.by_flag = False
        
    def read_file(self, path: str) -> list:
        with open (path, 'r') as f:
            data = f.readlines()
        return data
    
    def write_data(self, data: list, path: str):
        with open (path, 'w') as f:
            f.writelines(data)
    
    def update_number(self) -> list:
        data = self.read_file('./bugs.md')
        for line in data:
            if '# Byproduct bugs' in line:
                self.by_flag = True
            if not self.by_flag:
                self.num_bugs += line.count('](')
                self.num_confirmed += line.count('confirmed')
                self.num_fixed += line.count('fixed')
            else:
                self.num_by_bugs += line.count('](')
                self.num_by_confirmed += line.count('confirmed')
                self.num_by_fixed += line.count('fixed')
                
        self.num_confirmed += self.num_fixed
        self.num_by_confirmed += self.num_by_fixed
        if '(Byproduct bugs included)' not in data[1]:
            raise Exception("The first line of bugs.md should start with '(Byproduct bugs included)'")
        data[1] = '(Byproduct bugs included) Total bugs: **{}**, confirmed: **{}**, Fixed: **{}**.<br/>\n'.format(self.num_bugs + self.num_by_bugs, self.num_confirmed + self.num_by_confirmed, self.num_fixed + self.num_by_fixed)
        data[3] = '(Byproduct bugs excluded) Total bugs: **{}**, confirmed: **{}**, Fixed: **{}**.<br/>\n'.format(self.num_bugs, self.num_confirmed, self.num_fixed)
        self.write_data(data, './bugs.md')
        
if __name__ == '__main__':
    bug_counter = BugCounter()
    bug_counter.update_number()
