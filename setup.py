import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pybare", # Replace with your own username
    version="0.1.1",
    author="Noah Pederson",
    author_email="noah@packetlost.dev",
    description="A declarative implementation of BARE for Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://sr.ht/~chiefnoah/PyBARE/",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
