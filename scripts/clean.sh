#!/bin/bash

echo "Cleaning auxiliary LaTeX files..."

# Find all auxiliary files recursively and delete them
find . -type f \( -name "*.aux" -o -name "*.log" -o -name "*.out" -o -name "*.toc" -o -name "*.fls" -o -name "*.fdb_latexmk" \) -delete

echo "Clean complete!"
