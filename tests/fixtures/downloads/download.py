import csv, sys
import requests

import csv

def read_tsv(file_path):
    rows = []
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter='\t')
        for row in reader:
            rows.append(row)
    return rows

def get_translation_variant_validator(hgvs_c):
    print (f"\tChecking variant validator")
    server = "https://rest.variantvalidator.org"
    url = "/VariantValidator/variantvalidator/GRCh38/{}/select".format(hgvs_c)
    timeout = 90

    response = requests.get(server+url, headers={"Content-Type":"application/json"}, timeout=timeout)
    if not response.ok:
        return hgvs_c, False, None, None, None, None

    json = response.json()

    hg38_data = json[hgvs_c]["primary_assembly_loci"]["hg38"]["vcf"]

    chromosome = hg38_data.get("chr").replace("chr", "")
    position =  int(hg38_data.get("pos"))
    reference = hg38_data.get("ref")
    alternate = hg38_data.get("alt")
    print (f"\t\tAccepting {chromosome}:{position}:{reference}:{alternate}")

    return hgvs_c, True, chromosome, int(position), reference, alternate

def get_translation_ensembl(hgvs_c):
    print (f"\tChecking ensembl")
    server = "https://rest.ensembl.org"
    url = "/variant_recoder/human/{}?fields=None&vcf_string=1".format(hgvs_c)
    timeout = 90

    response = requests.get(server+url, headers={"Content-Type":"application/json"}, timeout=timeout)
    if not response.ok:
        return hgvs_c, False, None, None, None, None

    json = response.json()

    # Find the entry for the X chromosome
    for entry in json:
        key = list(entry.keys())[0]
        for item in entry[key]['vcf_string']:
            chromosome, position, reference, alternate = item.split("-")
            if chromosome == "X":
                print (f"\t\tAccepting {chromosome}:{position}:{reference}:{alternate}")
                return hgvs_c, True, chromosome, int(position), reference, alternate
            else:
                print (f"\t\tIgnoring {chromosome}:{position}:{reference}:{alternate}")

    print (f"None found")
    return hgvs_c, False, None, None, None, None


if __name__ == "__main__":
    print("Running")
    if len(sys.argv) != 4:
        print("Usage: python download.py <input_file> <ensembl_output_file> <variant_validator_output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file1 = sys.argv[2]
    output_file2 = sys.argv[3]
    print(f"Reading {input_file}")
    data = read_tsv(input_file)
    position=1
    total = len(data)
    print(f"Found {total} variants")
    
    hgvs_column_name = "hgvs_c"

    results = []
    # write file header, overwriting the existing file
    with open(output_file1, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter=',')
        writer.writerow(["HGVS", "Success", "Chromosome", "Position", "Ref", "Alt"])
    with open(output_file2, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file, delimiter=',')
        writer.writerow(["HGVS", "Success", "Chromosome", "Position", "Ref", "Alt"])

    # Lookup the ensembl API for each row and save the result in a matching file
    for row in data:
        hgvs_c = row.get(hgvs_column_name)
        
        print(f"Progress {position}/{total}")
        
        # write row, appending the existing file
        result1 = get_translation_ensembl(hgvs_c)
        with open(output_file1, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=',')
            writer.writerow(result1)
            
        # write row, appending the existing file        
        result2 = get_translation_variant_validator(hgvs_c)
        with open(output_file2, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=',')
            writer.writerow(result2)

        position = position + 1
        
        
        
        




