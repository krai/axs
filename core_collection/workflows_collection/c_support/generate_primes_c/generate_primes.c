#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cJSON.h"

int *sieve_of_eratosthenes(int n, int * size)
{
    int arr[n + 1];
    int *r = malloc(sizeof(int) * (n + 1));
    
    for (int i = 0; i <= n; i++){
        arr[i] = 1;
    }
    for (int i = 2; (i * i) <= n; i++) {
        if (arr[i] == 1) {
            for (int k = 2; i * k <= n; k++) {
                arr[ i * k ] = 0;
            }
        }
    }
    int j = 0;
    for (int i = 2; i <= n; i++) {
        if (arr[i] == 1) {
            r[j] = i;
            j++;
        }
    }
    *size = j;
    int *result = malloc(sizeof(int) * j);
    memcpy(result, r, sizeof(int) * j);
    free(r);

    return result;
}

int main(int argc, char **argv) {
    int size;
    int n = atoi(argv[1]);
    char *output_json_file_path = argv[2];

    char *output_json_string = NULL;

    cJSON *cjson_object = NULL;

    int *primes = sieve_of_eratosthenes(n, &size);
    if (!primes)
        printf("Error: can't create array");

    cjson_object = cJSON_CreateObject();

    if (!cjson_object)
        printf("Error: can't create array");

    cJSON *arr = cJSON_CreateIntArray(primes, size);
    
    cJSON_AddItemToObject(cjson_object, "primes", arr);

    output_json_string = cJSON_Print(cjson_object);

    cJSON_Delete(cjson_object);

    FILE *f = fopen(output_json_file_path, "w");
    fwrite(output_json_string, sizeof(char), strlen(output_json_string), f );

    free(output_json_string);

    fclose(f);

    return 0;
}
