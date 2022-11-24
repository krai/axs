#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cJSON.h"

int *factorizer (int num, int *pr, int size, int* n) {
    int k = 0;
    
    int *res = malloc(size* sizeof(int));
    
    for(int i = 0; i < size; i++)
        while (num % pr[i] == 0) {
            res[k] = pr[i];
            k++;
            num /= pr[i];
        }
    *n = k;
    return res;
}
char *load_json_file(char *filename) {
    char *buffer = 0;
    long length;
    FILE *f = fopen(filename, "rb");

    if(f){
      fseek(f, 0, SEEK_END);
      length = ftell (f);
      fseek(f, 0, SEEK_SET);
      buffer = malloc(length);
      if(buffer) {
        fread(buffer, 1, length, f);
      }
      fclose (f);
    }

    return buffer;
}

int main(int argc, char **argv) {
    char *input_json_string = load_json_file( argv[1] );
    char *output_json_file_path = argv[3];
    int num = atoi(argv[2]);

    char *output_json_string = NULL;

    cJSON *cjson_object = NULL;

    const cJSON *cjson_arr   = NULL;
    
    cJSON *elem = NULL;
    int *factorized_number=malloc(10); 
    
    int status = 0;
    int n= 0;
    cJSON *parsed_json = cJSON_Parse(input_json_string);

    if(parsed_json == NULL) {
        const char *error_ptr = cJSON_GetErrorPtr();
        if(error_ptr != NULL) {
            fprintf(stderr, "Error before: %s\n", error_ptr);
        }
        status = 0;
        goto end;
    }

    cjson_arr = cJSON_GetObjectItemCaseSensitive(parsed_json, "primes");
    int size = cJSON_GetArraySize(cjson_arr);
    int *arr = malloc(size * sizeof(int));
    
    for(int i=0; i< size; i++ ) {
        elem = cJSON_GetArrayItem(cjson_arr, i);
        arr[i] = elem->valueint;
    }
    factorized_number = factorizer (num, arr, size, &n);
    free(arr);

    cjson_object = cJSON_CreateObject();
    if (!cjson_object)
        printf("Error: can't create array");
    
    cJSON *cjson_arr_output = cJSON_CreateIntArray(factorized_number, n);

    cJSON_AddItemToObject(cjson_object, "factorized_number", cjson_arr_output);

    output_json_string = cJSON_Print(cjson_object);

    cJSON_Delete(cjson_object);

    FILE *f = fopen(output_json_file_path, "w");
    fwrite(output_json_string, sizeof(char), strlen(output_json_string), f );

    free(output_json_string);

    fclose(f);
end:
    cJSON_Delete(parsed_json);
    free(input_json_string);
    return 0;
}
