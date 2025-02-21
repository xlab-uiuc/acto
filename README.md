# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/xlab-uiuc/acto/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                          |    Stmts |     Miss |   Cover |   Missing |
|-------------------------------------------------------------- | -------: | -------: | ------: | --------: |
| acto/\_\_init\_\_.py                                          |        1 |        0 |    100% |           |
| acto/\_\_main\_\_.py                                          |       72 |       72 |      0% |     1-168 |
| acto/acto\_config.py                                          |       32 |        3 |     91% |     96-98 |
| acto/checker/\_\_init\_\_.py                                  |        0 |        0 |    100% |           |
| acto/checker/checker.py                                       |       10 |        1 |     90% |        20 |
| acto/checker/checker\_set.py                                  |       48 |       12 |     75% |59-60, 98-109 |
| acto/checker/impl/\_\_init\_\_.py                             |        0 |        0 |    100% |           |
| acto/checker/impl/consistency.py                              |      225 |       50 |     78% |74, 86-87, 95-133, 145-146, 180, 195-200, 234, 358, 391, 441, 444-462, 471-488 |
| acto/checker/impl/crash.py                                    |       31 |        3 |     90% |16, 21, 47 |
| acto/checker/impl/health.py                                   |       54 |        6 |     89% |20, 51, 84-90, 105, 132 |
| acto/checker/impl/operator\_log.py                            |       23 |        0 |    100% |           |
| acto/checker/impl/state\_compare.py                           |      100 |       22 |     78% |63, 74, 81, 88-98, 162-163, 172-178 |
| acto/checker/impl/state\_condition.py                         |       40 |       14 |     65% |23, 32, 37-49, 62, 70-72 |
| acto/checker/impl/test\_state\_compare.py                     |        9 |        0 |    100% |           |
| acto/checker/impl/tests/\_\_init\_\_.py                       |       39 |        0 |    100% |           |
| acto/checker/impl/tests/test\_crash.py                        |       15 |        0 |    100% |           |
| acto/checker/impl/tests/test\_health.py                       |       17 |        0 |    100% |           |
| acto/checker/impl/tests/test\_operator\_log.py                |       17 |        0 |    100% |           |
| acto/checker/impl/tests/test\_snapshot.py                     |       12 |        0 |    100% |           |
| acto/checker/impl/tests/test\_state.py                        |       42 |        0 |    100% |           |
| acto/cli/\_\_init\_\_.py                                      |        0 |        0 |    100% |           |
| acto/cli/collect\_system\_state.py                            |       21 |       21 |      0% |      1-58 |
| acto/cli/schema\_match.py                                     |       42 |       42 |      0% |      1-90 |
| acto/common.py                                                |      177 |       30 |     83% |54-55, 87, 119-122, 173, 232-235, 279-286, 288-293, 300-303, 326-337 |
| acto/constant.py                                              |        6 |        0 |    100% |           |
| acto/deploy.py                                                |      113 |       73 |     35% |21-43, 60-61, 72-75, 83-84, 86-89, 94, 104-184, 195-201, 205, 210 |
| acto/engine.py                                                |      479 |      368 |     23% |79-86, 105-108, 130-242, 271-308, 316-390, 407-608, 623-678, 691-730, 736-765, 771-779, 783-798, 830-832, 844-848, 894-900, 927-1092, 1102-1181 |
| acto/exception.py                                             |        2 |        2 |      0% |       1-2 |
| acto/input/\_\_init\_\_.py                                    |        0 |        0 |    100% |           |
| acto/input/constraint.py                                      |       22 |       14 |     36% |     19-32 |
| acto/input/get\_matched\_schemas.py                           |       54 |       22 |     59% |12, 47-51, 55-74 |
| acto/input/input.py                                           |      305 |       71 |     77% |75, 83, 88, 93, 98, 103, 108, 113, 118, 123, 137, 156, 194, 225-226, 235, 241-272, 317, 359-365, 545, 553-566, 574, 581, 585, 591, 595-615, 635, 637, 645-663 |
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
| acto/input/known\_schemas/statefulset\_schemas.py             |      186 |       92 |     51% |15-18, 21, 31-36, 42, 49-53, 56-58, 61-63, 66-70, 73-75, 78-80, 83, 90-93, 99-102, 105, 116-119, 123, 129, 132, 142-145, 149, 153-155, 158, 164, 167-170, 173, 176, 186-187, 190-193, 196-201, 204, 207, 218-221, 225, 231, 234, 250-253, 257, 262-263, 266, 274-277, 281, 287, 290 |
| acto/input/known\_schemas/storage\_schemas.py                 |      179 |       77 |     57% |13, 16, 25-30, 33, 36, 42, 48-53, 59, 67-70, 74, 79-80, 83, 89, 92-95, 98, 104-105, 108-111, 114-116, 122, 130-131, 135, 140, 145-148, 154-155, 158, 164, 181-184, 188, 197, 203-205, 211, 214, 228-231, 235, 244, 250-252, 258, 266-269, 273, 278, 282 |
| acto/input/kubernetes\_property.py                            |       26 |       26 |      0% |      1-92 |
| acto/input/property\_attribute.py                             |       10 |        0 |    100% |           |
| acto/input/test\_generators/\_\_init\_\_.py                   |       10 |        0 |    100% |           |
| acto/input/test\_generators/configuration.py                  |       40 |       30 |     25% |     19-93 |
| acto/input/test\_generators/cron\_job.py                      |       13 |        6 |     54% |10-25, 31-46 |
| acto/input/test\_generators/deployment.py                     |        8 |        3 |     62% |     12-27 |
| acto/input/test\_generators/generator.py                      |       97 |        7 |     93% |109, 273-275, 279-281 |
| acto/input/test\_generators/pod.py                            |      107 |        4 |     96% |311-318, 355-363 |
| acto/input/test\_generators/primitive.py                      |      303 |       98 |     68% |28, 30, 32, 38, 40, 44, 53-54, 70-82, 107, 111-112, 122, 128, 130, 134-135, 144, 150, 153, 156, 173, 187-188, 229, 233, 236, 239, 243, 250, 256, 267-273, 287-288, 463-468, 471-476, 479, 482-487, 490-493, 496, 502, 508, 530-531, 569, 572, 575, 592, 609-610, 642-667, 689-704, 713, 716, 719, 737 |
| acto/input/test\_generators/resource.py                       |       20 |        3 |     85% |     63-78 |
| acto/input/test\_generators/service.py                        |       12 |        6 |     50% |9-21, 29-44 |
| acto/input/test\_generators/stateful\_set.py                  |       26 |        0 |    100% |           |
| acto/input/test\_generators/storage.py                        |       13 |        0 |    100% |           |
| acto/input/testcase.py                                        |       63 |        5 |     92% |82, 93-97, 147, 153 |
| acto/input/testplan.py                                        |      183 |      123 |     33% |14-24, 27-29, 32, 35-42, 45, 48-67, 70-74, 78, 82, 85-91, 99-107, 110-121, 124, 127, 130, 133, 136-138, 141-151, 154-164, 167, 174-185, 188-194, 203-219, 222, 225, 239-244, 264, 272 |
| acto/input/value\_with\_schema.py                             |      345 |      126 |     63% |24, 29, 34, 39, 44, 49, 54, 59, 76, 82, 85-91, 110-145, 151, 159, 194, 203, 220, 223, 226-232, 251-270, 274, 276, 284, 301, 313, 315-318, 329, 332, 338, 356, 363, 365, 369, 375, 380-384, 389, 400-410, 414, 420, 425, 435, 441, 444, 458, 461-465, 473-480, 484, 486, 492, 499, 505, 519, 522-524, 527, 530, 533, 536 |
| acto/input/valuegenerator.py                                  |      620 |      396 |     36% |20, 24, 28, 32, 43, 47, 51, 55, 76-86, 90-104, 107, 110, 114, 117, 121-130, 133-139, 142, 145, 148, 151, 154, 157-167, 194-199, 202-213, 216, 219, 223, 226-231, 234-237, 240, 243-248, 251-254, 257, 260, 263, 266, 269, 273-282, 285, 288, 291, 294-304, 331-343, 346-347, 350, 353, 357, 360-365, 368-371, 374, 377-382, 385-388, 391, 394, 397, 400, 403, 406, 409-419, 446, 450-482, 485-496, 499-502, 505-508, 512-520, 523, 526, 529, 532, 535, 538-548, 573-589, 592-609, 612, 615, 619-621, 624-628, 631-632, 635-644, 647-653, 656-657, 660-670, 673, 676, 679, 682, 685, 688-698, 710-711, 714-724, 727-730, 733-736, 740, 748, 751-752, 755-765, 768-771, 774-777, 781, 791, 794-797, 800-814, 817, 820, 824, 827-832, 835, 838, 841-846, 849, 852, 855, 858, 861-871, 878, 881, 884, 887, 890, 894, 905, 911, 913, 916-919, 931, 933, 936-940, 943-946, 951, 955, 957, 961-962 |
| acto/k8s\_util/\_\_init\_\_.py                                |        0 |        0 |    100% |           |
| acto/k8s\_util/k8sutil.py                                     |       35 |        0 |    100% |           |
| acto/k8s\_util/test\_k8sutil.py                               |       34 |        0 |    100% |           |
| acto/kubectl\_client/\_\_init\_\_.py                          |        1 |        0 |    100% |           |
| acto/kubectl\_client/helm.py                                  |       26 |       19 |     27% |9-10, 14-18, 22-23, 36-52 |
| acto/kubectl\_client/kubectl.py                               |       38 |       29 |     24% |11-17, 28-34, 40-54, 64-77, 83-95 |
| acto/kubernetes\_engine/\_\_init\_\_.py                       |        0 |        0 |    100% |           |
| acto/kubernetes\_engine/base.py                               |       49 |       18 |     63% |73-92, 104, 118 |
| acto/kubernetes\_engine/k3d.py                                |       85 |       85 |      0% |     1-139 |
| acto/kubernetes\_engine/kind.py                               |      105 |       34 |     68% |68-70, 101, 107, 117-126, 135-139, 142-143, 146-160, 168, 173, 176, 187 |
| acto/kubernetes\_engine/minikube.py                           |      161 |      144 |     11% |26-32, 36-37, 41, 50-227, 230-244, 247-263, 270-281 |
| acto/lib/\_\_init\_\_.py                                      |        0 |        0 |    100% |           |
| acto/lib/dict.py                                              |       13 |        0 |    100% |           |
| acto/lib/operator\_config.py                                  |       64 |        7 |     89% |80-89, 207-211 |
| acto/lib/test\_dict.py                                        |       15 |        0 |    100% |           |
| acto/lib/test\_operator\_config.py                            |        9 |        0 |    100% |           |
| acto/monkey\_patch/\_\_init\_\_.py                            |        0 |        0 |    100% |           |
| acto/monkey\_patch/monkey\_patch.py                           |       79 |       30 |     62% |8-11, 18, 36, 39, 41, 45-56, 72-78, 90-95, 106 |
| acto/oracle\_handle.py                                        |       26 |       15 |     42% |21-24, 32-33, 46-60, 68 |
| acto/parse\_log/\_\_init\_\_.py                               |        1 |        0 |    100% |           |
| acto/parse\_log/parse\_log.py                                 |      105 |       34 |     68% |88-89, 94-97, 104-105, 110-115, 118-123, 125-130, 132-137, 142-144 |
| acto/post\_process/\_\_init\_\_.py                            |        0 |        0 |    100% |           |
| acto/post\_process/collect\_test\_result.py                   |       47 |       47 |      0% |     1-125 |
| acto/post\_process/post\_chain\_inputs.py                     |       41 |       41 |      0% |      1-65 |
| acto/post\_process/post\_diff\_test.py                        |      491 |      285 |     42% |75-76, 81, 99-100, 145-148, 244, 255, 259, 264-273, 278-293, 308, 318, 320, 322-326, 332-359, 374-387, 391-429, 445-458, 462-549, 586-587, 622, 642-652, 685, 694-739, 743-791, 797-858, 875, 880, 885, 889, 898-899, 901-949, 1000-1021, 1030-1042, 1047-1080, 1084 |
| acto/post\_process/post\_diff\_test\_test.py                  |       20 |        1 |     95% |       105 |
| acto/post\_process/post\_process.py                           |       33 |        7 |     79% |33-36, 43, 47, 57 |
| acto/post\_process/simple\_crash\_test.py                     |      162 |      126 |     22% |40-52, 61-74, 88-111, 129-143, 151-204, 233-246, 251-346, 350-387 |
| acto/post\_process/test\_post\_process.py                     |       28 |        1 |     96% |        75 |
| acto/reproduce.py                                             |      149 |      149 |      0% |     1-349 |
| acto/result.py                                                |      102 |       14 |     86% |57, 78, 81, 156-158, 188-189, 214, 229, 233-238, 264-265 |
| acto/result\_test.py                                          |        8 |        0 |    100% |           |
| acto/runner/\_\_init\_\_.py                                   |        1 |        0 |    100% |           |
| acto/runner/fault\_injection\_runner.py                       |       22 |       22 |      0% |      3-58 |
| acto/runner/runner.py                                         |      263 |      231 |     12% |42-88, 108-186, 190-197, 203-239, 246-282, 289-326, 330-333, 337-403, 407-410, 421-426, 442-448, 461-510, 514-518, 523-537, 548-585 |
| acto/schema/\_\_init\_\_.py                                   |       10 |        0 |    100% |           |
| acto/schema/anyof.py                                          |       48 |       16 |     67% |32, 38-46, 49, 60, 67-72 |
| acto/schema/array.py                                          |       97 |       31 |     68% |50, 62-71, 73-82, 92-99, 116, 121, 133, 136-141, 157, 163 |
| acto/schema/base.py                                           |      106 |       44 |     58% |31-42, 46, 50, 54-56, 59-71, 74-86, 89, 93-97, 111, 118, 123, 128, 133, 138, 177 |
| acto/schema/boolean.py                                        |       31 |        8 |     74% |17, 23, 32-35, 45, 48 |
| acto/schema/get\_total\_number\_schemas.py                    |       47 |       36 |     23% | 19-86, 93 |
| acto/schema/get\_total\_number\_schemas\_test.py              |        7 |        0 |    100% |           |
| acto/schema/integer.py                                        |       38 |       10 |     74% |18, 24-26, 36, 44-49, 51, 67 |
| acto/schema/number.py                                         |       41 |       18 |     56% |49, 55-57, 60, 63-68, 73, 76, 80-87, 90 |
| acto/schema/object.py                                         |      153 |       44 |     71% |50, 52, 57, 72-81, 83-92, 102-117, 143, 148, 172, 179-184, 188-192, 201-205, 222, 246 |
| acto/schema/oneof.py                                          |       81 |       61 |     25% |16-24, 28-36, 40, 43-45, 50-58, 61, 64, 67-69, 72, 75-76, 79-84, 87-97, 100-112 |
| acto/schema/opaque.py                                         |       29 |       15 |     48% |18, 21, 24-33, 36, 39, 42, 45 |
| acto/schema/schema.py                                         |       41 |        7 |     83% |23, 27, 33-36, 51 |
| acto/schema/string.py                                         |       54 |       15 |     72% |37, 43-45, 57-62, 67, 80-85, 88-92, 103 |
| acto/schema/under\_specified.py                               |       37 |       12 |     68% |14-16, 34, 39, 42, 49, 52, 55, 58, 63, 68 |
| acto/serialization.py                                         |       52 |       23 |     56% |16-19, 34, 36, 38, 40, 42, 45, 52-58, 65-71 |
| acto/snapshot.py                                              |       66 |       14 |     79% |83, 98-128, 144-149 |
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
| acto/system\_state/replica\_set.py                            |       27 |       12 |     56% |     35-58 |
| acto/system\_state/role.py                                    |       16 |        1 |     94% |        33 |
| acto/system\_state/role\_binding.py                           |       16 |        1 |     94% |        33 |
| acto/system\_state/secret.py                                  |       16 |        1 |     94% |        31 |
| acto/system\_state/service.py                                 |       16 |        1 |     94% |        36 |
| acto/system\_state/service\_account.py                        |       16 |        1 |     94% |        33 |
| acto/system\_state/stateful\_set.py                           |       29 |       14 |     52% |     38-76 |
| acto/system\_state/storage\_class.py                          |       16 |        1 |     94% |        28 |
| acto/trial.py                                                 |       26 |        2 |     92% |     38-39 |
| acto/utils/\_\_init\_\_.py                                    |       13 |        1 |     92% |        11 |
| acto/utils/acto\_timer.py                                     |       31 |       22 |     29% |10-15, 19, 22-33, 38-40, 44-47 |
| acto/utils/error\_handler.py                                  |       43 |       33 |     23% |15-35, 43-58, 63-82 |
| acto/utils/k8s\_helper.py                                     |       66 |       42 |     36% |26-32, 44-50, 62-69, 92, 107, 113-122, 127-129, 134-158 |
| acto/utils/preprocess.py                                      |       71 |       59 |     17% |17-39, 62-132, 137-171 |
| acto/utils/process\_with\_except.py                           |        9 |        9 |      0% |      1-13 |
| acto/utils/thread\_logger.py                                  |       17 |        5 |     71% |11-13, 24, 37 |
|                                                     **TOTAL** | **10121** | **4556** | **55%** |           |


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