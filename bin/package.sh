#!/usr/bin/env bash

DMGTitle="Clack";
DMGName="$(./clack --version)";
DMGBackground="clackbg.png";
DMGSize=1024;

# Creating an executable binary file
sudo echo "We can sudo";
echo "Packaging Clack.";
./build.sh;
# Rendering the readme file.
echo "Rendering the README file."
./render.sh;
# Creating a disk image with the binary file.
# http://stackoverflow.com/questions/96882/how-do-i-create-a-nice-looking-dmg-for-mac-os-x-using-command-line-tools
if [ -f "../dist/${DMGName}.dmg" ]
then
    rm "../dist/${DMGName}.dmg";
fi
mkdir -p ../tmp/clack;
cp clack ../tmp/clack/;
cp ../dist/README.pdf ../tmp/clack/;
mkdir ../tmp/clack/.background;
cp "../resources/${DMGBackground}" ../tmp/clack/.background/;
ln -s /usr/local/bin ../tmp/clack/UsrLocalBin;
chmod u+x ../tmp/clack/clack;
hdiutil create -srcfolder ../tmp/clack -volname "${DMGTitle}" -fs HFS+ -fsargs "-c c=64,a=16,e=16" -format UDRW -size ${DMGSize}k ../tmp.dmg;
device=$(hdiutil attach -readwrite -noverify -noautoopen "../tmp.dmg" | egrep '^/dev/' | sed 1q | awk '{print $1}');
sleep 5;
echo '
   tell application "Finder"
     tell disk "'${DMGTitle}'"
           open
           set current view of container window to icon view
           set toolbar visible of container window to false
           set statusbar visible of container window to false
           set the bounds of container window to {150, 150, 660, 570}
           set theViewOptions to the icon view options of container window
           set arrangement of theViewOptions to not arranged
           set icon size of theViewOptions to 100
           set background picture of theViewOptions to file ".background:'${DMGBackground}'"
           set position of item "clack" of container window to {100, 100}
           set position of item "UsrLocalBin" of container window to {400, 100}
           set position of item "README.pdf" of container window to {100, 300}
           close
           open
           update without registering applications
           delay 5
           close
     end tell
   end tell
' | osascript;
# make new alias file at container window to POSIX file "/usr/local/bin" with properties {name:"UsrLocalBin"}
sudo chmod -Rf go-w /Volumes/"${DMGTitle}";
sync;
sync;
hdiutil detach ${device};
hdiutil convert "../tmp.dmg" -format UDZO -imagekey zlib-level=9 -o "${DMGName}";
mv "${DMGName}.dmg" ../dist/;
rm -f ../tmp.dmg;
echo "Done with image, creating Zip Distribution file."
# Create a ZIP distro
if [ -f "../dist/${DMGName}.zip" ]
then
    rm "../dist/${DMGName}.zip";
fi
cd ../tmp;
rm -rf clack/.*
rm -f clack/UsrLocalBin
mv clack ${DMGName};
zip -qr ${DMGName}.zip ${DMGName};
mv ${DMGName}.zip ../dist/;
echo "Done with zip file, cleaning up.";
rm -rf ../tmp/${DMGName}
cd ../bin;
echo "Done.";
