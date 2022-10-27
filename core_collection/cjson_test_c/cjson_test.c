#include <stdio.h>
#include <stdlib.h>
#include "cJSON.h"

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

    const cJSON *city   = NULL;
    const cJSON *alpha  = NULL;
    const cJSON *beta   = NULL;
    const cJSON *gamma  = NULL;

    int status = 0;
    cJSON *parsed_json = cJSON_Parse(input_json_string);
    if(parsed_json == NULL) {
        const char *error_ptr = cJSON_GetErrorPtr();
        if(error_ptr != NULL) {
            fprintf(stderr, "Error before: %s\n", error_ptr);
        }
        status = 0;
        goto end;
    }

    city = cJSON_GetObjectItemCaseSensitive(parsed_json, "city");
    if(cJSON_IsString(city) && (city->valuestring != NULL)) {
        printf("City name: %s\n", city->valuestring);
    }

    alpha = cJSON_GetObjectItemCaseSensitive(parsed_json, "alpha");
    if(cJSON_IsNumber(alpha)) {
        printf("alpha (unsigned int): %d\n", alpha->valueint);
    }

    beta = cJSON_GetObjectItemCaseSensitive(parsed_json, "beta");
    if(cJSON_IsNumber(beta)) {
        printf("beta (signed int): %d\n", beta->valueint);
    }

    gamma = cJSON_GetObjectItemCaseSensitive(parsed_json, "gamma");
    if(cJSON_IsNumber(gamma)) {
        printf("gamma (double): %f\n", gamma->valuedouble);
    }
end:
    cJSON_Delete(parsed_json);
    free(input_json_string);
    return 0;
}
