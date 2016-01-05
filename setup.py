from setuptools import find_packages, setup

with open('description.rst') as f:
    long_description = f.read()

version = __import__('clack').VERSION

setup(
    name='clack-cli',
    version=version,
    author='R Meurders',
    author_email='pypi+clack@rmnl.net',
    license='MIT',
    description='Clack is a Command Line API Calling Kit based on Click.',
    long_description=long_description,
    keywords='development command line tool api interface jwplayer',
    url='https://github.com/rmnl/clack',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click>=5.0',
        'httplib2>=0.9',
        'urllib3>=1.10.1',
        'keyring>=5.7.1',
    ],
    entry_points={
        'console_scripts': [
            'clack = clack.__main__:clack'
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Utilities',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
    ],
)
