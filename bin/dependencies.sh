#!/usr/bin/env bash

# Barebones script to pull in dependencies.

CLICK_VERSION="4.0";
HTTPLIB2_VERSION="0.9";
URLLIB3_VERSION="1.10.1";

CLICK_URL="https://github.com/mitsuhiko/click/archive/${CLICK_VERSION}.tar.gz";
HTTPLIB2_URL="https://github.com/jcgregorio/httplib2/archive/v${HTTPLIB2_VERSION}.tar.gz";
URLLIB3_URL="https://github.com/shazow/urllib3/archive/${URLLIB3_VERSION}.tar.gz";


if [ ! -d "../tmp/dependencies" ]
then
  if [ -f "../tmp/dependencies" ]
  then
    rm "../tmp/dependencies";
  fi
  mkdir "../tmp/dependencies";
fi

# Click
echo "Checking for Click";
if [ -d "../tmp/dependencies/click" ]
then
  echo "Click was found, dependency already resolved.";
else
  echo "Downloading Click";
  if [ -f "../tmp/click.tgz" ]
  then
    rm "../tmp/click.tgz";
  fi
  wget -O ../tmp/click.tgz $CLICK_URL;
  tar xvzf ../tmp/click.tgz --directory ../tmp/dependencies
  mv "../tmp/dependencies/click-${CLICK_VERSION}" ../tmp/dependencies/click;
  rm ../tmp/click.tgz;
  echo "Click dependency resolved";
fi

# HTTPLIB2
echo "Checking for Httplib2";
if [ -d "../tmp/dependencies/httplib2" ]
then
  echo "Httplib2 was found, dependency already resolved.";
else
  echo "Downloading Httplib2";
  if [ -f "../tmp/httplib2.tgz" ]
  then
    rm "../tmp/httplib2.tgz";
  fi
  wget -O ../tmp/httplib2.tgz $HTTPLIB2_URL;
  tar xvzf ../tmp/httplib2.tgz --directory ../tmp/dependencies
  mv "../tmp/dependencies/httplib2-${HTTPLIB2_VERSION}" ../tmp/dependencies/httplib2;
  rm ../tmp/httplib2.tgz;
  echo "Httplib2 dependency resolved";
fi

# URLLIB3
echo "Checking for Urllib3";
if [ -d "../tmp/dependencies/urllib3" ]
then
  echo "Urllib3 was found, dependency already resolved.";
else
  echo "Downloading Urllib3";
  if [ -f "../tmp/urllib3.tgz" ]
  then
    rm "../tmp/urllib3.tgz";
  fi
  wget -O ../tmp/urllib3.tgz $URLLIB3_URL;
  tar xvzf ../tmp/urllib3.tgz --directory ../tmp/dependencies
  mv "../tmp/dependencies/urllib3-${URLLIB3_VERSION}" ../tmp/dependencies/urllib3;
  rm ../tmp/urllib3.tgz;
  echo "Urllib3 dependency resolved";
fi

echo "Done resolving dependencies."