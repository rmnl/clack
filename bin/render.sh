#!/usr/bin/env bash

# Render the readme file.
if [ -f "../dist/README.pdf" ]
then
    rm "../dist/README.pdf";
fi
cd ../;
grip readme.md --export readme.html;
wkhtmltopdf readme.html README.pdf;
rm readme.html;
mv README.pdf dist/;
cd bin;
