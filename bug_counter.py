num_bugs = 0
num_confirmed = 0
num_fixed = 0
num_by_bugs = 0
num_by_confirmed = 0
num_by_fixed = 0
by_flag = False

with open ('./bugs.md', 'r') as f:
    data = f.readlines()
    

for line in data:
    if '# Byproduct bugs' in line:
        by_flag = True
    if not by_flag:
        num_bugs += line.count('](')
        num_confirmed += line.count('confirmed')
        num_fixed += line.count('fixed')
    else:
        num_by_bugs += line.count('](')
        num_by_confirmed += line.count('confirmed')
        num_by_fixed += line.count('fixed')
        
num_confirmed += num_fixed
num_by_confirmed += num_by_fixed
if '(Byproduct bugs included)' not in data[1]:
    raise Exception("The first line of bugs.md should start with '(Byproduct bugs included)'")
data[1] = '(Byproduct bugs included) Total bugs: **{}**, confirmed: **{}**, fixed: **{}**.<br/>\n'.format(num_bugs + num_by_bugs, num_confirmed + num_by_confirmed, num_fixed + num_by_fixed)
data[3] = '(Byproduct bugs excluded) Total bugs: **{}**, confirmed: **{}**, fixed: **{}**.<br/>\n'.format(num_bugs, num_confirmed, num_fixed)

with open ('./bugs.md', 'w') as f:
    f.writelines(data)
    