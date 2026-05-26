# parse_wi_soa

Parse Wisconsin **Statement of Assessment** (SOA) PDF forms into CSV.

Extracts Lines 1-9 (real estate classes) from Page 1 of each form, including municipality header fields. Handles multi-page PDFs containing multiple municipalities.

## Requirements

- Python 3
- [pdftotext](https://poppler.freedesktop.org/) (part of Poppler)

### Install pdftotext

```sh
# macOS
brew install poppler

# Debian/Ubuntu
sudo apt-get install poppler-utils
```

## Usage

Parse one or more PDFs, outputting CSV to stdout:

```sh
bin/parse_wi_soa form1.pdf form2.pdf > output.csv
```

### Output columns

| Column | Source |
|--------|--------|
| Town/Village/City | Form header |
| Municipality Name | Form header |
| County Name | Form header |
| Line No. | 1-9 |
| Real Estate | Class description |
| Total Land (Col A) | Parcel count |
| Improvements (Col B) | Parcel count |
| No. of Acres (Col C) | Whole numbers only |
| Value of Land (Col D) | Assessed value |
| Value of Improvements (Col E) | Assessed value |
| Total Value of Land and Improvements (Col F) | Assessed value |

## Testing

Run tests against the validated fixtures in `validated/`:

```sh
bin/test
```

Validate an arbitrary directory of PDF/CSV pairs:

```sh
bin/validate_wi_soa /path/to/pairs/
```

To add a new test fixture, place a matching `name.pdf` and `name.csv` in `validated/`. The test suite auto-discovers all pairs.

## How it works

1. Extracts text from each PDF using `pdftotext -layout`
2. Locates column positions dynamically from the `(Col. A)` through `(Col. F)` header row
3. Parses the municipality type, name, and county from the `FOR ... OF ...` header
4. Assigns each numeric value on Lines 1-9 to its nearest column by character position
5. Normalizes county names (strips trailing "COUNTY") and outputs plain integers

## License

MIT
