# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/xlab-uiuc/acto/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                          |    Stmts |     Miss |   Cover |   Missing |
|-------------------------------------------------------------- | -------: | -------: | ------: | --------: |
| acto/\_\_init\_\_.py                                          |        0 |        0 |    100% |           |
| acto/\_\_main\_\_.py                                          |       88 |       88 |      0% |     1-174 |
| acto/acto\_config.py                                          |       32 |        3 |     91% |     96-98 |
| acto/checker/\_\_init\_\_.py                                  |        0 |        0 |    100% |           |
| acto/checker/checker.py                                       |       10 |        1 |     90% |        20 |
| acto/checker/checker\_set.py                                  |       48 |       13 |     73% |29, 54-55, 94-105 |
| acto/checker/impl/\_\_init\_\_.py                             |        0 |        0 |    100% |           |
| acto/checker/impl/consistency.py                              |      224 |       50 |     78% |72, 84-85, 93-131, 143-144, 178, 193-198, 232, 356, 388, 433, 436-454, 463-480 |
| acto/checker/impl/crash.py                                    |       31 |        3 |     90% |16, 21, 47 |
| acto/checker/impl/health.py                                   |       52 |        5 |     90% |46, 87-93, 111, 141 |
| acto/checker/impl/operator\_log.py                            |       23 |        0 |    100% |           |
| acto/checker/impl/state\_compare.py                           |       76 |        3 |     96% |62, 73, 80 |
| acto/checker/impl/state\_condition.py                         |       40 |       14 |     65% |23, 32, 37-49, 62, 70-72 |
| acto/checker/impl/test\_state\_compare.py                     |        9 |        0 |    100% |           |
| acto/checker/impl/tests/\_\_init\_\_.py                       |       39 |        0 |    100% |           |
| acto/checker/impl/tests/test\_crash.py                        |       15 |        0 |    100% |           |
| acto/checker/impl/tests/test\_health.py                       |       15 |        0 |    100% |           |
| acto/checker/impl/tests/test\_operator\_log.py                |       16 |        0 |    100% |           |
| acto/checker/impl/tests/test\_snapshot.py                     |       12 |        0 |    100% |           |
| acto/checker/impl/tests/test\_state.py                        |       42 |        0 |    100% |           |
| acto/common.py                                                |      164 |       31 |     81% |33, 66, 450-453, 504, 563-566, 608-615, 617-622, 629-632, 647-648, 655-666 |
| acto/constant.py                                              |        6 |        0 |    100% |           |
| acto/deploy.py                                                |       96 |       77 |     20% |15-41, 47-62, 66, 73-123, 131-137, 140-145, 149 |
| acto/engine.py                                                |      494 |      494 |      0% |    3-1203 |
| acto/exception.py                                             |        2 |        2 |      0% |       1-2 |
| acto/input/\_\_init\_\_.py                                    |        2 |        0 |    100% |           |
| acto/input/get\_matched\_schemas.py                           |       54 |       22 |     59% |12, 47-51, 55-74 |
| acto/input/input.py                                           |      438 |      300 |     32% |28-34, 74, 91, 104, 113, 118, 123, 128, 133, 138, 143, 148, 153, 167, 184, 196-201, 204, 216, 251-288, 298-648, 672-684, 687-702, 706, 710, 717, 723, 727-747, 756, 773, 776-783, 795, 797, 803, 806-819, 824, 832-849, 852-858 |
| acto/input/k8s\_schemas.py                                    |      218 |       44 |     80% |76-83, 96, 103, 113, 123, 130, 133, 155, 158, 177, 183, 186, 193, 196, 203, 206, 214, 301-302, 310, 316, 320, 405, 414-457 |
| acto/input/known\_schemas/\_\_init\_\_.py                     |       10 |        0 |    100% |           |
| acto/input/known\_schemas/base.py                             |       53 |       13 |     75% |17-18, 28, 37, 46-47, 56-57, 66, 75, 84-85, 93 |
| acto/input/known\_schemas/cronjob\_schemas.py                 |       76 |       33 |     57% |13, 16-19, 22, 25, 36-39, 42-47, 50, 53, 59, 62-65, 68, 71, 82, 85-90, 93, 96, 113, 117-119, 131, 137, 140 |
| acto/input/known\_schemas/deployment\_schemas.py              |       59 |       25 |     58% |16, 22-27, 30-32, 35, 38, 54-57, 65-67, 70, 78-81, 91, 94 |
| acto/input/known\_schemas/known\_schema.py                    |       75 |       39 |     48% |28, 31-34, 37, 43, 46-48, 51, 54, 81-84, 102-113, 117-135 |
| acto/input/known\_schemas/pod\_disruption\_budget\_schemas.py |       56 |       22 |     61% |14-17, 21, 25-27, 30, 41-44, 48, 54, 57, 68-71, 81, 84 |
| acto/input/known\_schemas/pod\_schemas.py                     |      797 |      266 |     67% |16-19, 23, 28, 32, 40-43, 47, 52, 61-64, 68, 73, 83, 92, 151, 156, 160, 167, 171, 178, 182, 238, 242, 247, 251, 294, 298, 303, 307, 335, 338, 341, 344, 347, 350, 353, 356, 359, 362, 365, 368, 393, 397, 400-405, 408, 414, 417, 420, 428, 431, 434, 437, 445, 453, 481, 488-494, 503, 507, 539, 543, 572, 575, 578, 581, 584, 587, 590, 619, 623, 626-631, 634, 642, 645, 648, 664-667, 670-672, 675, 684, 690, 693-696, 699, 702, 713-714, 717-719, 722, 725, 736, 739, 742, 745-748, 752, 758, 761-765, 768, 774, 777, 780, 783, 786, 789, 792, 795, 798, 801, 804, 807, 810, 813, 816, 840, 845, 849-857, 860, 866, 869, 872, 875, 878, 881, 884, 887, 890, 893, 896, 899, 902, 905, 908, 929, 933-935, 938-943, 946, 959, 964, 974, 980, 986, 989, 992, 1032, 1036-1038, 1041, 1054, 1059, 1065, 1068-1071, 1074, 1077, 1088-1091, 1094-1096, 1102, 1108, 1111-1114, 1117, 1120, 1133-1136, 1139-1141, 1147, 1153, 1156-1159, 1162, 1165, 1176-1179, 1182-1184, 1190, 1196, 1199-1202, 1205, 1212, 1215-1217, 1223, 1238, 1243, 1247, 1274, 1278, 1291, 1296, 1302, 1305, 1308, 1314, 1317, 1320-1322, 1325, 1342, 1345, 1348, 1374, 1378-1381, 1384, 1402, 1408, 1411, 1414, 1421, 1427, 1473 |
| acto/input/known\_schemas/resource\_schemas.py                |      161 |       59 |     63% |20-24, 27, 30, 33-37, 40, 43, 59-68, 73, 77, 82, 85-88, 91, 105, 107, 112, 128, 134-137, 140, 143, 155, 169, 182, 189, 194-198, 201, 210-213, 217, 225, 232, 237, 252, 270, 275 |
| acto/input/known\_schemas/service\_schemas.py                 |      178 |       67 |     62% |13, 16, 19, 25-30, 33, 36, 42, 45-48, 51, 54, 64-67, 70-73, 79, 85, 88-91, 94, 101-102, 105-108, 111, 114, 127, 142, 180, 184, 208, 214, 217, 220, 228-231, 235, 240, 244-246, 249, 257-258, 261, 264, 277-280, 284, 288-290, 293 |
| acto/input/known\_schemas/statefulset\_schemas.py             |      186 |       61 |     67% |15-18, 21, 31-36, 42, 49-53, 56-58, 61-63, 66-70, 73-75, 78-80, 83, 90-93, 99-102, 105, 132, 149, 154, 158, 164, 167-170, 173, 176, 190-193, 196-201, 207, 225, 230, 234, 262, 266, 290 |
| acto/input/known\_schemas/storage\_schemas.py                 |      179 |       76 |     58% |13, 16, 25-30, 33, 36, 42, 48-53, 59, 67-70, 74, 79-80, 83, 89, 92-95, 98, 104-105, 108-111, 114-116, 122, 130-131, 135, 140, 145-148, 154-155, 158, 164, 181-184, 193, 197, 203-205, 211, 214, 228-231, 244, 250-252, 258, 266-269, 273, 278, 282 |
| acto/input/testcase.py                                        |       55 |       20 |     64% |40-50, 53, 56, 59, 62-66, 95-96, 100, 103, 109, 116, 119 |
| acto/input/testplan.py                                        |      183 |      137 |     25% |14-24, 27-29, 32, 35-42, 45, 48-67, 70-74, 78, 82, 85-91, 99-107, 110-121, 124, 127, 130, 133, 136-138, 141-151, 154-164, 167, 174-185, 188-194, 200, 203-219, 222, 225, 231, 239-244, 247, 250, 253, 259-260, 263-269, 272, 275, 278 |
| acto/input/value\_with\_schema.py                             |      337 |      218 |     35% |16, 20, 24, 28, 32, 36, 40, 54, 58, 61-67, 70-76, 86-114, 117-124, 128-137, 141-149, 152-156, 159, 162, 166, 180, 183, 186-192, 195-201, 211-230, 233-240, 243, 247-256, 260-272, 275-279, 282, 285, 289, 301, 307, 312, 314, 316, 320, 324, 329-333, 337-340, 349-359, 362-369, 373-376, 380-385, 388-391, 405, 408-412, 416, 421-428, 431-434, 437-439, 442-445, 448-451, 462, 465, 468, 485-498 |
| acto/input/valuegenerator.py                                  |      620 |      389 |     37% |20, 24, 28, 32, 43, 47, 51, 55, 76-86, 90-104, 107, 110, 114, 117, 121-130, 133-139, 142, 145, 148, 151, 154, 157-167, 194-199, 202-213, 216, 219, 223, 226-231, 234-237, 240, 243-248, 251-254, 257, 260, 263, 266, 269, 273-282, 285, 288, 291, 294-304, 331-343, 346-347, 350, 353, 357, 360-365, 368-371, 374, 377-382, 385-388, 391, 394, 397, 400, 403, 406, 409-419, 450-482, 485-496, 499-502, 505-508, 512-520, 523, 526, 529, 532, 535, 538-548, 573-589, 592-609, 612, 615, 619-621, 624-628, 631-632, 635-644, 647-653, 656-657, 660-670, 673, 676, 679, 682, 685, 688-698, 710-711, 714-724, 727-730, 733-736, 740, 748, 751-752, 755-765, 768-771, 774-777, 781, 794-797, 800-814, 817, 820, 824, 827-832, 835, 838, 841-846, 849, 852, 855, 858, 861-871, 881, 884, 887, 890, 894, 913, 919, 931, 933, 936-940, 943-946, 951, 955, 957, 961-962 |
| acto/k8s\_util/\_\_init\_\_.py                                |        0 |        0 |    100% |           |
| acto/k8s\_util/k8sutil.py                                     |       35 |        0 |    100% |           |
| acto/k8s\_util/test\_k8sutil.py                               |       34 |        0 |    100% |           |
| acto/kubectl\_client/\_\_init\_\_.py                          |        1 |        0 |    100% |           |
| acto/kubectl\_client/kubectl.py                               |       23 |       18 |     22% |8-14, 23-29, 37-44 |
| acto/kubernetes\_engine/\_\_init\_\_.py                       |        0 |        0 |    100% |           |
| acto/kubernetes\_engine/base.py                               |       54 |       22 |     59% |30, 34, 38, 42, 46, 49-67, 79 |
| acto/kubernetes\_engine/k3d.py                                |       85 |       85 |      0% |     1-139 |
| acto/kubernetes\_engine/kind.py                               |       99 |       32 |     68% |51-53, 57-58, 84, 90, 99-102, 108-112, 115-116, 119-131, 139, 144, 147, 158 |
| acto/kubernetes\_engine/minikube.py                           |        3 |        3 |      0% |       1-5 |
| acto/lib/\_\_init\_\_.py                                      |        0 |        0 |    100% |           |
| acto/lib/dict.py                                              |       13 |        0 |    100% |           |
| acto/lib/operator\_config.py                                  |       46 |        3 |     93% |   115-118 |
| acto/lib/test\_dict.py                                        |       15 |        0 |    100% |           |
| acto/lib/test\_operator\_config.py                            |        9 |        0 |    100% |           |
| acto/monkey\_patch/\_\_init\_\_.py                            |        0 |        0 |    100% |           |
| acto/monkey\_patch/monkey\_patch.py                           |       79 |       24 |     70% |9, 18, 36, 39, 41, 45-56, 76, 90-95, 106 |
| acto/oracle\_handle.py                                        |       24 |       13 |     46% |15-18, 26-27, 39-46, 54 |
| acto/parse\_log/\_\_init\_\_.py                               |        1 |        0 |    100% |           |
| acto/parse\_log/parse\_log.py                                 |       78 |       19 |     76% |71-74, 84-86, 89-91, 96-98, 116-124 |
| acto/post\_process/\_\_init\_\_.py                            |        0 |        0 |    100% |           |
| acto/post\_process/collect\_test\_result.py                   |       27 |       27 |      0% |      1-59 |
| acto/post\_process/post\_chain\_inputs.py                     |       41 |       41 |      0% |      1-65 |
| acto/post\_process/post\_diff\_test.py                        |      406 |      230 |     43% |67-68, 75, 92-93, 138-141, 218, 228, 232, 237-246, 281, 283, 285-289, 294-321, 334-347, 350-387, 401-414, 417-506, 523-527, 561, 569-615, 618-640, 645-710, 725, 729, 738-739, 741-788, 814-847, 851 |
| acto/post\_process/post\_process.py                           |       33 |        7 |     79% |177-180, 187, 191, 201 |
| acto/post\_process/simple\_crash\_test.py                     |      163 |      127 |     22% |39-51, 60-73, 87-110, 128-142, 150-203, 232-245, 250-346, 350-387 |
| acto/post\_process/test\_post\_process.py                     |       28 |        1 |     96% |        67 |
| acto/reproduce.py                                             |      124 |      124 |      0% |     1-276 |
| acto/result.py                                                |       99 |       14 |     86% |58, 79, 82, 143-145, 175-176, 201, 216, 220-225, 251-252 |
| acto/result\_test.py                                          |        8 |        0 |    100% |           |
| acto/runner/\_\_init\_\_.py                                   |        1 |        0 |    100% |           |
| acto/runner/runner.py                                         |      296 |      265 |     10% |40-87, 106-185, 189-196, 202-238, 245-281, 288-325, 329-332, 336-377, 381-384, 395-400, 416-422, 435-592, 596-600, 605-619, 630-667 |
| acto/schema/\_\_init\_\_.py                                   |       10 |        0 |    100% |           |
| acto/schema/anyof.py                                          |       44 |       20 |     55% |26, 30-38, 41, 44, 47-49, 52, 55-60 |
| acto/schema/array.py                                          |       70 |       29 |     59% |31, 43-52, 57, 59-62, 71-78, 81-83, 86-88, 91, 94, 97, 103 |
| acto/schema/base.py                                           |      102 |       57 |     44% |13-15, 18-20, 23, 26-37, 40, 43, 46-48, 51-61, 64-74, 77, 80-86, 95, 100, 105, 110, 114, 118, 142, 145-149 |
| acto/schema/boolean.py                                        |       27 |       10 |     63% |16, 20, 23, 26, 29-32, 35, 38 |
| acto/schema/integer.py                                        |       26 |        9 |     65% |17, 21-23, 26, 29, 32, 35, 38 |
| acto/schema/number.py                                         |       30 |       11 |     63% |30-32, 35-37, 40, 43, 46, 49, 52 |
| acto/schema/object.py                                         |      117 |       48 |     59% |44, 46, 51, 66-75, 80, 83, 94-109, 112-120, 123-126, 129, 132, 148, 151-158, 168 |
| acto/schema/oneof.py                                          |       44 |       30 |     32% |13-19, 22, 25-27, 30-38, 41, 44, 47-49, 52, 55-60 |
| acto/schema/opaque.py                                         |       17 |        6 |     65% |13, 16, 19, 22, 25, 28 |
| acto/schema/schema.py                                         |       42 |        8 |     81% |21, 25, 31-34, 49-50 |
| acto/schema/string.py                                         |       27 |        9 |     67% |25, 29-31, 34, 37, 40, 43, 46 |
| acto/serialization.py                                         |       52 |       27 |     48% |16-19, 34, 36, 38, 40, 42, 45, 48-58, 65-71 |
| acto/snapshot.py                                              |       66 |       14 |     79% |81, 96-126, 142-147 |
| acto/trial.py                                                 |       26 |        2 |     92% |     38-39 |
| acto/utils/\_\_init\_\_.py                                    |       13 |        1 |     92% |        11 |
| acto/utils/acto\_timer.py                                     |       31 |       22 |     29% |10-15, 19, 22-33, 38-40, 44-47 |
| acto/utils/error\_handler.py                                  |       43 |       33 |     23% |15-35, 43-58, 63-82 |
| acto/utils/k8s\_helper.py                                     |       64 |       51 |     20% |21-27, 39-45, 57-61, 73-79, 83-91, 95-102, 106-127 |
| acto/utils/preprocess.py                                      |       69 |       58 |     16% |17-73, 93-141, 147-192 |
| acto/utils/process\_with\_except.py                           |        9 |        9 |      0% |      1-13 |
| acto/utils/thread\_logger.py                                  |       15 |        3 |     80% | 9, 18, 28 |
|                                                     **TOTAL** | **8040** | **4087** | **49%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/xlab-uiuc/acto/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/xlab-uiuc/acto/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/xlab-uiuc/acto/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/xlab-uiuc/acto/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fxlab-uiuc%2Facto%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/xlab-uiuc/acto/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.