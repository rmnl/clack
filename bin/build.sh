#!/usr/bin/env bash

echo "Creating a standalone application binary"
if [ -f clack ]
then
  rm clack;
fi
echo "Resolving dependencies."
./dependencies.sh;
cd ../clack;
zip -qr ../bin/clack.zip *;
cd ../bin;
echo '#!/usr/bin/env python' | cat - clack.zip > clack;
chmod +x clack;
rm clack.zip;
echo "Done.";
