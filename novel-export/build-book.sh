#!/usr/bin/env bash

# Call this script with 3 arguments, in order:
#		1. Path to the top-level folder containing your book's Markdown files.
#		2. Path to the metadata JSON file for your book.
#		3. The desired output filename (without extension) for the generated ePub and PDF books.
# Your generated books will be in the same folder you called this script from.

# Handle script arguments.
if [ $# -lt 3 ]; then
	echo "Usage: $0 PATH_TO_MARKDOWN_FOLDER METADATA_JSON_FILE OUTPUT_FILENAME_WITHOUT_EXTENSION"
	echo "ePub and PDF books will be created in same directory script is called from."
	exit 1
fi

MARKDOWN_DIR="$1"
METADATA_JSON="$2"
OUTPUT_BASENAME="$3"
TEMP_MASTER_MARKDOWN_FILE="temp-book-master.md"

if [ ! -d "${MARKDOWN_DIR}" ]; then
	echo "$MARKDOWN_DIR should be a directory, but isn't."
	exit 1
elif [ ! -f "${METADATA_JSON}" ]; then
	echo "$METADATA_JSON should be a file, but isn't."
	exit 1
fi

# Clean up any old output files.
#rm "$PWD/$OUTPUT_BASENAME".{epub,pdf} 2> /dev/null

# Recursively concatenate all markdown files into a master document, separated by blank lines.
> $TEMP_MASTER_MARKDOWN_FILE
find "${MARKDOWN_DIR}" \( -name "*.md" -o -name "*.mdown" -o -name "*.markdown" \) -type f | sort -V | while read f
do
	cat "$f" >> $TEMP_MASTER_MARKDOWN_FILE
	echo >> $TEMP_MASTER_MARKDOWN_FILE
done

# Prepare extra metadata.
meta_date=$(date +"%Y-%m-%d")
meta_date_year=$(date +"%Y")
extra_json="{\"date\":\"${meta_date}\",\"date-year\":\"${meta_date_year}\"}"

# Replace any metadata placeholders in the master document.
# (See comments in the 'replace-placeholders.py' Python script for how this works.)
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
python3 "$SCRIPT_DIR"/replace-placeholders.py $TEMP_MASTER_MARKDOWN_FILE $METADATA_JSON "$extra_json"

# Invoke pandoc on the master document, once for ePub and once for PDF.
pandoc --defaults="${SCRIPT_DIR}/options-epub.yaml" --defaults="${SCRIPT_DIR}/options-shared.yaml" \
       --metadata-file=$METADATA_JSON --metadata=date="$meta_date" --metadata=date-year:"$meta_date_year" \
       --output=$OUTPUT_BASENAME.epub $TEMP_MASTER_MARKDOWN_FILE
pandoc --defaults="${SCRIPT_DIR}/options-pdf.yaml" --defaults="${SCRIPT_DIR}/options-shared.yaml" \
       --metadata-file=$METADATA_JSON --metadata=date="$meta_date" --metadata=date-year:"$meta_date_year" \
       --output=$OUTPUT_BASENAME.pdf $TEMP_MASTER_MARKDOWN_FILE

# Clean up temporary files.
rm $TEMP_MASTER_MARKDOWN_FILE
