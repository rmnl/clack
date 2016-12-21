from setuptools import find_packages, setup

with open('description.rst') as f:
    long_description = f.read()

version = __import__('clack.version').version.VERSION

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
        'Click>=6.6',
        'keyring>=5.7.1',
        'requests>=2.10.0',
        'jwplatform>=1.1.0',
        'Pygments>=2.1.3',
    ],
    entry_points={
        'console_scripts': [
            'clack = clack.cli:clack',
            # 'clack = clack.cli:call',
            # 'clack_config = clack.cli:settings_group',
        ],
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Utilities',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
    ],
)
