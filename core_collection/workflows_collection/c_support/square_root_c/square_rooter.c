#include <math.h>
#include <stdio.h>

/*  This program takes a square root of a number given from the command line
    and prints the result in the standard output */

int main(int argc, char *argv[]) {
    if(argc>1) {
        float area;
        sscanf(argv[1], "%f", &area);
        float side = sqrt( area );
        printf("When square's area is %.1f its side is %.2f\n", area, side);
    } else {
        printf("Usage:\n\t%s <area>\n", argv[0]);
    }

}
