# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/xlab-uiuc/acto/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                          |    Stmts |     Miss |   Cover |   Missing |
|-------------------------------------------------------------- | -------: | -------: | ------: | --------: |
| acto/\_\_init\_\_.py                                          |        1 |        0 |    100% |           |
| acto/\_\_main\_\_.py                                          |       72 |       72 |      0% |     1-169 |
| acto/acto\_config.py                                          |       32 |        3 |     91% |     96-98 |
| acto/checker/\_\_init\_\_.py                                  |        0 |        0 |    100% |           |
| acto/checker/checker.py                                       |       10 |        1 |     90% |        20 |
| acto/checker/checker\_set.py                                  |       48 |       13 |     73% |29, 54-55, 94-105 |
| acto/checker/impl/\_\_init\_\_.py                             |        0 |        0 |    100% |           |
| acto/checker/impl/consistency.py                              |      225 |       50 |     78% |74, 86-87, 95-133, 145-146, 180, 195-200, 234, 358, 391, 441, 444-462, 471-488 |
| acto/checker/impl/crash.py                                    |       31 |        3 |     90% |16, 21, 47 |
| acto/checker/impl/health.py                                   |       52 |        5 |     90% |46, 87-93, 111, 141 |
| acto/checker/impl/operator\_log.py                            |       23 |        0 |    100% |           |
| acto/checker/impl/state\_compare.py                           |       76 |        3 |     96% |62, 73, 80 |
| acto/checker/impl/state\_condition.py                         |       40 |       14 |     65% |23, 32, 37-49, 62, 70-72 |
| acto/checker/impl/test\_state\_compare.py                     |        9 |        0 |    100% |           |
| acto/checker/impl/tests/\_\_init\_\_.py                       |       39 |        0 |    100% |           |
| acto/checker/impl/tests/test\_crash.py                        |       15 |        0 |    100% |           |
| acto/checker/impl/tests/test\_health.py                       |       15 |        0 |    100% |           |
| acto/checker/impl/tests/test\_operator\_log.py                |       17 |        0 |    100% |           |
| acto/checker/impl/tests/test\_snapshot.py                     |       12 |        0 |    100% |           |
| acto/checker/impl/tests/test\_state.py                        |       42 |        0 |    100% |           |
| acto/cli/\_\_init\_\_.py                                      |        0 |        0 |    100% |           |
| acto/cli/collect\_system\_state.py                            |       21 |       21 |      0% |      1-58 |
| acto/cli/schema\_match.py                                     |       42 |       42 |      0% |      1-90 |
| acto/common.py                                                |      164 |       28 |     83% |66, 450-453, 504, 563-566, 608-615, 617-622, 629-632, 655-666 |
| acto/constant.py                                              |        6 |        0 |    100% |           |
| acto/deploy.py                                                |       96 |       66 |     31% |15-41, 55, 66, 73-122, 130-136, 139-144, 148 |
| acto/engine.py                                                |      460 |      361 |     22% |74-79, 100-212, 240-276, 284-358, 375-570, 585-637, 650-689, 695-724, 728-743, 776-778, 790-794, 824, 840-842, 850, 875-1031, 1043-1169 |
| acto/exception.py                                             |        2 |        2 |      0% |       1-2 |
| acto/input/\_\_init\_\_.py                                    |        0 |        0 |    100% |           |
| acto/input/get\_matched\_schemas.py                           |       54 |       22 |     59% |12, 47-51, 55-74 |
| acto/input/input.py                                           |      266 |       63 |     76% |65, 74, 79, 84, 89, 94, 99, 104, 109, 114, 128, 147, 161-166, 168, 181, 212-213, 222, 267, 309-315, 416, 424-437, 445, 452, 458, 462-482, 502, 504, 512-530 |
| acto/input/k8s\_schemas.py                                    |      348 |       65 |     81% |63, 66, 69, 84, 115-117, 151, 164, 174, 177, 180, 200, 204, 232, 241, 252, 255, 258, 268, 288, 396, 398, 400, 406, 410, 414-417, 426-427, 435, 439-441, 445, 472, 482, 509, 626, 635-638, 659-674, 678, 687-730 |
| acto/input/known\_schemas/\_\_init\_\_.py                     |       10 |        0 |    100% |           |
| acto/input/known\_schemas/base.py                             |       53 |       14 |     74% |17-18, 24, 28, 37, 46-47, 56-57, 66, 75, 84-85, 93 |
| acto/input/known\_schemas/cronjob\_schemas.py                 |       76 |       33 |     57% |13, 16-19, 22, 25, 36-39, 42-47, 50, 53, 59, 62-65, 68, 71, 82, 85-90, 93, 96, 113, 117-119, 131, 137, 140 |
| acto/input/known\_schemas/deployment\_schemas.py              |       59 |       26 |     56% |16, 22-27, 30-32, 35, 38, 54-57, 61, 66-67, 70, 78-81, 85, 91, 94 |
| acto/input/known\_schemas/known\_schema.py                    |       75 |       50 |     33% |28, 31-34, 37, 43, 46-48, 51, 54, 81-84, 88-99, 102-113, 117-135 |
| acto/input/known\_schemas/pod\_disruption\_budget\_schemas.py |       56 |       21 |     62% |14-17, 21, 27, 30, 41-44, 48, 54, 57, 68-71, 75, 81, 84 |
| acto/input/known\_schemas/pod\_schemas.py                     |      797 |      349 |     56% |16-19, 23, 28, 32, 40-43, 47, 52, 61-64, 68, 73, 83, 92, 144-147, 151, 156, 160, 167, 171, 178, 182, 232-235, 238, 242, 247, 251, 288-291, 294, 298, 303, 307, 335, 338, 341, 344, 347, 350, 353, 356, 359, 362, 365, 368, 381-384, 388, 393, 397, 400-405, 408, 414, 417, 420, 428, 431, 434, 437, 445, 453, 475-478, 481, 488-494, 498, 503, 507, 527-530, 534, 539, 543, 572, 575, 578, 581, 584, 587, 590, 607-610, 614, 619, 623, 626-631, 634, 642, 645, 648, 654-655, 658-661, 664-667, 670-672, 675, 684, 690, 693-696, 699, 702, 713-714, 717-719, 722, 725, 736, 739, 742, 745-748, 752, 758, 761-765, 768, 774, 777, 780, 783, 786, 789, 792, 795, 798, 801, 804, 807, 810, 813, 816, 840, 845, 849-857, 860, 866, 869, 872, 875, 878, 881, 884, 887, 890, 893, 896, 899, 902, 905, 908, 929, 933-935, 938-943, 946, 954-955, 959, 964, 970-971, 974, 980, 986, 989, 992, 1020-1023, 1027, 1036-1038, 1041, 1049-1050, 1054, 1059, 1065, 1068-1071, 1074, 1077, 1088-1091, 1094-1096, 1099, 1102, 1108, 1111-1114, 1117, 1120, 1129-1130, 1133-1136, 1139-1141, 1144, 1147, 1153, 1156-1159, 1162, 1165, 1176-1179, 1182-1184, 1187, 1190, 1196, 1199-1202, 1205, 1212, 1215-1217, 1220, 1223, 1231-1234, 1238, 1243, 1247, 1262-1265, 1269, 1274, 1278, 1286-1287, 1290-1293, 1296, 1302, 1305, 1308, 1314, 1317, 1320-1322, 1325, 1342, 1345, 1348, 1362-1365, 1369, 1374, 1378-1381, 1384, 1392-1393, 1396-1399, 1402, 1408, 1411, 1414, 1421, 1424, 1427, 1457-1460, 1464, 1470, 1473 |
| acto/input/known\_schemas/resource\_schemas.py                |      161 |       79 |     51% |20-24, 27, 30, 33-37, 40, 43, 57-68, 73, 77, 82, 85-88, 91, 99-100, 105, 107, 112, 118-125, 128, 134-137, 140, 143, 155, 162-165, 169, 182, 189, 194-198, 201, 210-213, 217, 225, 232, 237, 245-248, 252, 263, 269-272, 275 |
| acto/input/known\_schemas/service\_schemas.py                 |      178 |       86 |     52% |13, 16, 19, 25-30, 33, 36, 42, 45-48, 51, 54, 64-67, 70-73, 76, 79, 85, 88-91, 94, 101-102, 105-108, 111, 114, 120-121, 124, 127, 135-136, 139, 142, 168-171, 175, 179-181, 184, 192-195, 199, 205, 208, 214, 217, 220, 228-231, 235, 244-246, 249, 257-258, 261, 264, 277-280, 284, 288-290, 293 |
| acto/input/known\_schemas/statefulset\_schemas.py             |      186 |       94 |     49% |15-18, 21, 31-36, 42, 49-53, 56-58, 61-63, 66-70, 73-75, 78-80, 83, 90-93, 99-102, 105, 116-119, 123, 129, 132, 142-145, 149, 153-155, 158, 164, 167-170, 173, 176, 186-187, 190-193, 196-201, 204, 207, 218-221, 225, 229-231, 234, 250-253, 257, 262-263, 266, 274-277, 281, 287, 290 |
| acto/input/known\_schemas/storage\_schemas.py                 |      179 |       77 |     57% |13, 16, 25-30, 33, 36, 42, 48-53, 59, 67-70, 74, 79-80, 83, 89, 92-95, 98, 104-105, 108-111, 114-116, 122, 130-131, 135, 140, 145-148, 154-155, 158, 164, 181-184, 188, 197, 203-205, 211, 214, 228-231, 235, 244, 250-252, 258, 266-269, 273, 278, 282 |
| acto/input/kubernetes\_property.py                            |       26 |       26 |      0% |      1-92 |
| acto/input/property\_attribute.py                             |       10 |        0 |    100% |           |
| acto/input/test\_generators/\_\_init\_\_.py                   |        9 |        0 |    100% |           |
| acto/input/test\_generators/cron\_job.py                      |       13 |        6 |     54% |10-25, 31-46 |
| acto/input/test\_generators/deployment.py                     |        8 |        3 |     62% |     12-27 |
| acto/input/test\_generators/generator.py                      |       96 |        7 |     93% |106, 269-271, 275-277 |
| acto/input/test\_generators/pod.py                            |      107 |        4 |     96% |311-318, 355-363 |
| acto/input/test\_generators/primitive.py                      |      295 |      106 |     64% |27, 29, 31, 37, 39, 43, 52-53, 87, 91-92, 97-104, 107, 113, 115, 119-120, 126-133, 136, 142, 145, 148, 160-171, 185-186, 227, 231, 234, 237, 241, 248, 254, 266-277, 291-292, 467-472, 475-480, 483, 486-491, 494-497, 500, 506, 512, 524-535, 549-550, 587, 590, 593, 605-616, 630-631, 648, 670-683, 688-693, 701, 704, 707, 719-730 |
| acto/input/test\_generators/resource.py                       |       20 |        3 |     85% |     63-78 |
| acto/input/test\_generators/service.py                        |       12 |        6 |     50% |9-21, 29-44 |
| acto/input/test\_generators/stateful\_set.py                  |       26 |        0 |    100% |           |
| acto/input/test\_generators/storage.py                        |       13 |        0 |    100% |           |
| acto/input/testcase.py                                        |       61 |        5 |     92% |76, 87-91, 141, 147 |
| acto/input/testplan.py                                        |      183 |      123 |     33% |14-24, 27-29, 32, 35-42, 45, 48-67, 70-74, 78, 82, 85-91, 99-107, 110-121, 124, 127, 130, 133, 136-138, 141-151, 154-164, 167, 174-185, 188-194, 203-219, 222, 225, 239-244, 264, 272 |
| acto/input/value\_with\_schema.py                             |      345 |      126 |     63% |24, 29, 34, 39, 44, 49, 54, 59, 76, 82, 85-91, 110-145, 151, 159, 194, 203, 220, 223, 226-232, 251-270, 274, 276, 284, 301, 313, 315-318, 329, 332, 338, 356, 363, 365, 369, 375, 380-384, 389, 400-410, 414, 420, 425, 435, 441, 444, 458, 461-465, 473-480, 484, 486, 492, 499, 505, 519, 522-524, 527, 530, 533, 536 |
| acto/input/valuegenerator.py                                  |      620 |      396 |     36% |20, 24, 28, 32, 43, 47, 51, 55, 76-86, 90-104, 107, 110, 114, 117, 121-130, 133-139, 142, 145, 148, 151, 154, 157-167, 194-199, 202-213, 216, 219, 223, 226-231, 234-237, 240, 243-248, 251-254, 257, 260, 263, 266, 269, 273-282, 285, 288, 291, 294-304, 331-343, 346-347, 350, 353, 357, 360-365, 368-371, 374, 377-382, 385-388, 391, 394, 397, 400, 403, 406, 409-419, 446, 450-482, 485-496, 499-502, 505-508, 512-520, 523, 526, 529, 532, 535, 538-548, 573-589, 592-609, 612, 615, 619-621, 624-628, 631-632, 635-644, 647-653, 656-657, 660-670, 673, 676, 679, 682, 685, 688-698, 710-711, 714-724, 727-730, 733-736, 740, 748, 751-752, 755-765, 768-771, 774-777, 781, 791, 794-797, 800-814, 817, 820, 824, 827-832, 835, 838, 841-846, 849, 852, 855, 858, 861-871, 878, 881, 884, 887, 890, 894, 905, 911, 913, 916-919, 931, 933, 936-940, 943-946, 951, 955, 957, 961-962 |
| acto/k8s\_util/\_\_init\_\_.py                                |        0 |        0 |    100% |           |
| acto/k8s\_util/k8sutil.py                                     |       35 |        0 |    100% |           |
| acto/k8s\_util/test\_k8sutil.py                               |       34 |        0 |    100% |           |
| acto/kubectl\_client/\_\_init\_\_.py                          |        1 |        0 |    100% |           |
| acto/kubectl\_client/kubectl.py                               |       23 |       18 |     22% |8-14, 23-29, 37-44 |
| acto/kubernetes\_engine/\_\_init\_\_.py                       |        0 |        0 |    100% |           |
| acto/kubernetes\_engine/base.py                               |       46 |       17 |     63% |73-92, 104 |
| acto/kubernetes\_engine/k3d.py                                |       85 |       85 |      0% |     1-139 |
| acto/kubernetes\_engine/kind.py                               |      104 |       34 |     67% |68-70, 101, 107, 116-125, 134-138, 141-142, 145-159, 167, 172, 175, 186 |
| acto/kubernetes\_engine/minikube.py                           |      161 |      144 |     11% |26-32, 36-37, 41, 50-227, 230-244, 247-263, 270-281 |
| acto/lib/\_\_init\_\_.py                                      |        0 |        0 |    100% |           |
| acto/lib/dict.py                                              |       13 |        0 |    100% |           |
| acto/lib/operator\_config.py                                  |       44 |        3 |     93% |   144-148 |
| acto/lib/test\_dict.py                                        |       15 |        0 |    100% |           |
| acto/lib/test\_operator\_config.py                            |        9 |        0 |    100% |           |
| acto/monkey\_patch/\_\_init\_\_.py                            |        0 |        0 |    100% |           |
| acto/monkey\_patch/monkey\_patch.py                           |       79 |       30 |     62% |8-11, 18, 36, 39, 41, 45-56, 72-78, 90-95, 106 |
| acto/oracle\_handle.py                                        |       24 |       13 |     46% |15-18, 26-27, 39-46, 54 |
| acto/parse\_log/\_\_init\_\_.py                               |        1 |        0 |    100% |           |
| acto/parse\_log/parse\_log.py                                 |       88 |       22 |     75% |79-82, 92-94, 97-99, 101-103, 108-110, 128-136 |
| acto/post\_process/\_\_init\_\_.py                            |        0 |        0 |    100% |           |
| acto/post\_process/collect\_test\_result.py                   |       45 |       45 |      0% |     1-117 |
| acto/post\_process/post\_chain\_inputs.py                     |       41 |       41 |      0% |      1-65 |
| acto/post\_process/post\_diff\_test.py                        |      478 |      266 |     44% |69-70, 75, 93-94, 139-142, 219, 230, 234, 239-248, 288, 290, 292-296, 302-329, 344-357, 361-399, 415-428, 432-519, 556-557, 592, 612-616, 649, 658-703, 707-755, 761-822, 839, 843, 852-853, 855-903, 954-975, 984-996, 1001-1034, 1038 |
| acto/post\_process/post\_diff\_test\_test.py                  |       20 |        1 |     95% |       105 |
| acto/post\_process/post\_process.py                           |       33 |        7 |     79% |33-36, 43, 47, 57 |
| acto/post\_process/simple\_crash\_test.py                     |      162 |      126 |     22% |40-52, 61-74, 88-111, 129-143, 151-204, 233-246, 251-346, 350-387 |
| acto/post\_process/test\_post\_process.py                     |       28 |        1 |     96% |        67 |
| acto/reproduce.py                                             |      149 |      149 |      0% |     1-349 |
| acto/result.py                                                |       99 |       14 |     86% |57, 78, 81, 142-144, 174-175, 200, 215, 219-224, 250-251 |
| acto/result\_test.py                                          |        8 |        0 |    100% |           |
| acto/runner/\_\_init\_\_.py                                   |        1 |        0 |    100% |           |
| acto/runner/runner.py                                         |      294 |      263 |     11% |41-87, 106-184, 188-195, 201-237, 244-280, 287-324, 328-331, 335-376, 380-383, 394-399, 415-421, 434-589, 593-597, 602-616, 627-664 |
| acto/schema/\_\_init\_\_.py                                   |       10 |        0 |    100% |           |
| acto/schema/anyof.py                                          |       48 |       19 |     60% |32, 38-46, 49, 55-57, 60, 67-72 |
| acto/schema/array.py                                          |       85 |       32 |     62% |47, 59-68, 70-79, 89-96, 104-106, 109, 116-121, 136, 142 |
| acto/schema/base.py                                           |      106 |       44 |     58% |31-42, 46, 50, 54-56, 59-71, 74-86, 89, 93-97, 111, 118, 123, 128, 133, 138, 177 |
| acto/schema/boolean.py                                        |       31 |        8 |     74% |17, 23, 29, 32-35, 48 |
| acto/schema/get\_total\_number\_schemas.py                    |       47 |       36 |     23% | 19-86, 93 |
| acto/schema/get\_total\_number\_schemas\_test.py              |        7 |        0 |    100% |           |
| acto/schema/integer.py                                        |       38 |       12 |     68% |18, 24-26, 32-33, 36, 44-49, 51, 67 |
| acto/schema/number.py                                         |       37 |       14 |     62% |49, 55-57, 60, 63, 66, 69, 73-80, 83 |
| acto/schema/object.py                                         |      141 |       42 |     70% |49, 51, 56, 71-80, 82-91, 101-116, 132-135, 138, 162, 169-174, 202, 226 |
| acto/schema/oneof.py                                          |       48 |       33 |     31% |14-22, 28, 31-33, 38-46, 49, 52, 55-57, 60, 63-64, 67-72 |
| acto/schema/opaque.py                                         |       19 |        7 |     63% |15, 18, 21, 24, 27, 30, 33 |
| acto/schema/schema.py                                         |       41 |        7 |     83% |23, 27, 33-36, 51 |
| acto/schema/string.py                                         |       40 |        8 |     80% |36, 42-44, 50, 53, 66, 75 |
| acto/serialization.py                                         |       52 |       23 |     56% |16-19, 34, 36, 38, 40, 42, 45, 52-58, 65-71 |
| acto/snapshot.py                                              |       66 |       14 |     79% |81, 96-126, 142-147 |
| acto/system\_state/\_\_init\_\_.py                            |        0 |        0 |    100% |           |
| acto/system\_state/cluster\_role.py                           |       16 |        1 |     94% |        30 |
| acto/system\_state/cluster\_role\_binding.py                  |       17 |        1 |     94% |        31 |
| acto/system\_state/config\_map.py                             |       16 |        1 |     94% |        31 |
| acto/system\_state/cron\_job.py                               |       16 |        1 |     94% |        31 |
| acto/system\_state/daemon\_set.py                             |       25 |       10 |     60% |     35-64 |
| acto/system\_state/deployment.py                              |       31 |       16 |     48% |     35-70 |
| acto/system\_state/endpoints.py                               |       16 |        1 |     94% |        31 |
| acto/system\_state/ingress.py                                 |       16 |        1 |     94% |        37 |
| acto/system\_state/job.py                                     |       16 |        1 |     94% |        31 |
| acto/system\_state/kubernetes\_object.py                      |      109 |       40 |     63% |70-126, 140, 144, 160, 165, 177, 181, 190, 193, 205, 214, 217, 229 |
| acto/system\_state/kubernetes\_system\_state.py               |      105 |       17 |     84% |72, 84-97, 188, 227 |
| acto/system\_state/network\_policy.py                         |       16 |        1 |     94% |        33 |
| acto/system\_state/persistent\_volume.py                      |       16 |        1 |     94% |        28 |
| acto/system\_state/persistent\_volume\_claim.py               |       16 |        1 |     94% |        33 |
| acto/system\_state/pod.py                                     |       29 |       14 |     52% |     35-60 |
| acto/system\_state/replica\_set.py                            |       25 |       10 |     60% |     34-52 |
| acto/system\_state/role.py                                    |       16 |        1 |     94% |        33 |
| acto/system\_state/role\_binding.py                           |       16 |        1 |     94% |        33 |
| acto/system\_state/secret.py                                  |       16 |        1 |     94% |        31 |
| acto/system\_state/service.py                                 |       16 |        1 |     94% |        36 |
| acto/system\_state/service\_account.py                        |       16 |        1 |     94% |        33 |
| acto/system\_state/stateful\_set.py                           |       27 |       12 |     56% |     38-67 |
| acto/system\_state/storage\_class.py                          |       16 |        1 |     94% |        28 |
| acto/trial.py                                                 |       26 |        2 |     92% |     38-39 |
| acto/utils/\_\_init\_\_.py                                    |       13 |        1 |     92% |        11 |
| acto/utils/acto\_timer.py                                     |       31 |       22 |     29% |10-15, 19, 22-33, 38-40, 44-47 |
| acto/utils/error\_handler.py                                  |       43 |       33 |     23% |15-35, 43-58, 63-82 |
| acto/utils/k8s\_helper.py                                     |       64 |       51 |     20% |21-27, 39-45, 57-61, 73-79, 83-91, 95-102, 106-127 |
| acto/utils/preprocess.py                                      |       72 |       60 |     17% |17-83, 105-161, 166-200 |
| acto/utils/process\_with\_except.py                           |        9 |        9 |      0% |      1-13 |
| acto/utils/thread\_logger.py                                  |       15 |        3 |     80% | 9, 18, 28 |
|                                                     **TOTAL** | **9709** | **4368** | **55%** |           |


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