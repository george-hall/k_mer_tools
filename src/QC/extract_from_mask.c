
/*******************************************************************************
 * Copyright (c) 2015 Genome Research Ltd. 
 *  
 * Author: George Hall <gh10@sanger.ac.uk> 
 * 
 * This file is part of K-mer Toolkit. 
 * 
 * K-mer Toolkit is free software: you can redistribute it and/or modify it under 
 * the terms of the GNU General Public License as published by the Free Software 
 * Foundation; either version 3 of the License, or (at your option) any later 
 * version. 
 *  
 * This program is distributed in the hope that it will be useful, but WITHOUT 
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS 
 * FOR A PARTICULAR PURPOSE. See the GNU General Public License for more 
 * details. 
 *  
 * You should have received a copy of the GNU General Public License along with 
 * this program. If not, see <http://www.gnu.org/licenses/>. 
 ******************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
	char* name;
	unsigned long start,
				  end;
} location;

location get_next_loc(FILE* mask_locs);
char* get_chromo_name(FILE* ref);
	
int main(int argc, char** argv) {
	FILE *ref,
		 *mask_locs;

	if (argc != 3) {
		fprintf(stderr, "Usage: <reference> <location file>\n");
		exit(EXIT_FAILURE);
	}

	if ((ref = fopen(argv[1], "r")) == NULL) {
		fprintf(stderr, "ERROR: Could not open reference file\n");
		exit(EXIT_FAILURE);
	}

	if ((mask_locs = fopen(argv[2], "r")) == NULL) {
		fprintf(stderr, "ERROR: Could not open location file\n");
		exit(EXIT_FAILURE);
	}


	int num_locations = 0;	
	char c, /* Counts along masked reference */
		 d; /* Counts along unmasked reference */
	while ((c = getc(mask_locs)) != EOF) {
		if (c == '\n') {
			num_locations++;
		}
	}

	rewind(mask_locs);
	char* chromo_name;
	getc(ref); /* Move pointer onto start of first chromo name, instead of '>' character */
	chromo_name = get_chromo_name(ref);
	if ((d = getc(ref)) == EOF) {
		fprintf(stderr, "ERROR: Reference file too short\n");
		exit(EXIT_FAILURE);
	} 

	int iCount = 0;
	unsigned long base_index = 1;

	/* For each location caught in mask */
	while (iCount < num_locations) {
		location loc;
		loc = get_next_loc(mask_locs);
		if (loc.end < loc.start) {
			fprintf(stderr, "ERROR: End point of location cannot be smaller than start point\n");
			exit(EXIT_FAILURE);
		}

		/* Make sure that we are in the correct chromosome */
		if (strcmp(chromo_name, loc.name) != 0)	{
			while (strcmp(chromo_name, loc.name) != 0) {
				while ((d = getc(ref)) != '>');
				free(chromo_name);	
				chromo_name = get_chromo_name(ref);
			}
			if ((d = getc(ref)) == EOF) {
				fprintf(stderr, "ERROR: Reference file too short\n");
				exit(EXIT_FAILURE);
			} 

			base_index = 1;
		}

		/* Navigate to correct location on chromosome */
		while (base_index < loc.start) {
			if ((d = getc(ref)) == EOF) {
				fprintf(stderr, "ERROR: Reference file too short [2]\n");
				exit(EXIT_FAILURE);
			}
			else if (d == 'A' || d == 'C' || d == 'G' || d == 'T' || d == 'N') {
				base_index++;
			}
			else if (d == '>') {
				fprintf(stderr, "ERROR: Reached end of chromosome without finding location\n");
				exit(EXIT_FAILURE);
			}
		}
			
		size_t str_len_required = ((loc.end - loc.start) + 2);
		char sequence[str_len_required];
		int i = 0;
		while (base_index <= loc.end ) {
			if (d == 'A' || d == 'C' || d == 'G' || d == 'T' || d == 'N') {
				sequence[i++] = d;
			}
			else if (d == '>') {
				fprintf(stderr, "ERROR: Reached end of chromosome without finding location\n");
				exit(EXIT_FAILURE);
			}

			if ((d = getc(ref)) == EOF) {
				fprintf(stderr, "ERROR: Reference file too short [3]\n");
				exit(EXIT_FAILURE);
			}
			if (d == 'A' || d == 'C' || d == 'G' || d == 'T' || d == 'N') {
				base_index++;
			}
		}
		sequence[i] = '\0';

		/* Only print sequences of length >= 100 */
		if ((str_len_required - 1) >= 100) {
			printf(">%s_%lu_%lu\n%s\n", loc.name, loc.start, loc.end, sequence);
		}
		iCount++;
	}
	
	free(chromo_name);
	fclose(ref);
	fclose(mask_locs);

	return 0;
}

char* get_chromo_name(FILE* ref) {
	int chromo_name_buffsize = 60;
	char* chromo_name;
	char d;
	if ((chromo_name = malloc(chromo_name_buffsize * sizeof(char))) == NULL) {
		fprintf(stderr, "Out of memory\n");
		exit(EXIT_FAILURE);
	}
	int chromo_name_index = 0;
	if ((d = getc(ref)) == EOF) {
		fprintf(stderr, "Unexpected end of file\n");
		exit(EXIT_FAILURE);
	}
	while ((d != '\n') && (d != ' ')) {

		if (d == EOF) {
			fprintf(stderr, "Unexpected end of file\n");
			exit(EXIT_FAILURE);
		}
		
		if (chromo_name_index == (chromo_name_buffsize - 1)) {
			chromo_name_buffsize *= 2;
			char* tmp = realloc(chromo_name, chromo_name_buffsize * sizeof(char));
			if (tmp != NULL) {
				chromo_name = tmp;
			}
			else {
				fprintf(stderr, "Out of memory\n");
				free(chromo_name);
				exit(EXIT_FAILURE);
			}
		}
		chromo_name[chromo_name_index++] = d;
		if ((d = getc(ref)) == EOF) {
			fprintf(stderr, "Unexpected end of file\n");
			exit(EXIT_FAILURE);
		}
	}

	while (d != '\n') {
		if ((d = getc(ref)) == EOF) {
			fprintf(stderr, "Unexpected end of file\n");
			exit(EXIT_FAILURE);
		}
	}
	
	chromo_name[chromo_name_index] = '\0';

	return chromo_name;
}

location get_next_loc(FILE* mask_locs) {
	char c;
	char* str;
	if ((str = malloc(100)) == NULL) {
		fprintf(stderr, "ERROR: Out of memory\n");
		exit(EXIT_FAILURE);
	}
	size_t buffsize = 100;
	int i = 0;

	while ((c = getc(mask_locs)) != '\n') {
		if (c == EOF) {
			fprintf(stderr, "Unexpected end of file\n");
			exit(EXIT_FAILURE);
		}

		/* Need to reallocate memory */
		if (i == (buffsize - 1)) {
			char* tmp = realloc(str, buffsize *= 2);

			if (tmp == NULL) {
				fprintf(stderr, "ERROR: Out of memory\n");
				free(str);
				exit(EXIT_FAILURE);
			}

			else {
				str = tmp;
			}
		}

		str[i++] = c;
	}

	str[i] = '\0';
	location loc;

	loc.name = strtok(str, " ");
	loc.start = strtoul(strtok(NULL, " "), NULL, 10);
	loc.end = strtoul(strtok(NULL, " "), NULL, 10);

	free(str);
	
	return loc;

}
