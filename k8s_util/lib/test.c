#include <stdio.h>
#include "k8sutil.h"

int main(){
    char *name = "-92743e6047801799";
    printf("The string after parsing is: %s\n", parse(name));
    return 0;
}