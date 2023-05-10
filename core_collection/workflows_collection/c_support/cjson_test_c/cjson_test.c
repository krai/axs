#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cJSON.h"

char *convert_to_uppercase(char *str) {
    char *newstr = malloc(strlen(str));
    strcpy(newstr, str);
    if ( newstr[0] >= 'a' && newstr[0] <= 'z' )
        newstr[0] = newstr[0] + 'A' - 'a';
    return newstr;
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
    char *output_json_file_path = argv[2];

    char *output_json_string = NULL;

    cJSON *cjson_object = NULL;

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

    // add values to output json file

    cjson_object = cJSON_CreateObject();
    cJSON *c = parsed_json->child;
    while (c != NULL) {
        switch (c->type) {
            case cJSON_String: {
                                   cJSON_AddStringToObject(cjson_object,convert_to_uppercase(c->string), c->valuestring);
                                   break;
                               }
            case cJSON_Number: {
                                   cJSON_AddNumberToObject(cjson_object,convert_to_uppercase(c->string), c->valuedouble);
                                   break;
                               }
        };
        c = c->next;
    }

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
