FROM --platform=linux/amd64 debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV WINEDEBUG=-all

RUN echo "--- Installing Wine and tools ---" && \
    dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        wine wine64 wine32 wget unzip ca-certificates xvfb xauth procps && \
    rm -rf /var/lib/apt/lists/* && \
    echo "--- Wine installed ---"

RUN echo "--- Initializing Wine prefix ---" && \
    xvfb-run wineboot --init 2>/dev/null; \
    while pgrep wineserver > /dev/null; do sleep 1; done && \
    echo "--- Wine prefix ready ---"

ARG PYTHON_VERSION=3.11.9
ENV PYDIR=/root/.wine/drive_c/Python311

RUN echo "--- Downloading Python ${PYTHON_VERSION} embeddable package ---" && \
    wget -q "https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-embed-amd64.zip" \
        -O /tmp/python.zip && \
    mkdir -p "$PYDIR" && \
    unzip -q /tmp/python.zip -d "$PYDIR" && \
    rm /tmp/python.zip && \
    sed -i 's/^#import site/import site/' "$PYDIR/python311._pth" && \
    echo "DLLs" >> "$PYDIR/python311._pth" && \
    echo "Lib" >> "$PYDIR/python311._pth" && \
    echo "--- Python extracted ---"

RUN echo "--- Installing pip ---" && \
    wget -q https://bootstrap.pypa.io/get-pip.py -O /tmp/get-pip.py && \
    wine C:/Python311/python.exe /tmp/get-pip.py 2>&1 | tail -3 && \
    while pgrep wineserver > /dev/null; do sleep 1; done && \
    rm /tmp/get-pip.py && \
    echo "--- pip installed ---"

RUN echo "--- Installing tkinter from MSIs (native extract) ---" && \
    apt-get update && apt-get install -y --no-install-recommends msitools && \
    rm -rf /var/lib/apt/lists/* && \
    wget -q "https://www.python.org/ftp/python/${PYTHON_VERSION}/amd64/tcltk.msi" -O /tmp/tcltk.msi && \
    wget -q "https://www.python.org/ftp/python/${PYTHON_VERSION}/amd64/lib.msi" -O /tmp/lib.msi && \
    mkdir -p /tmp/msi_out && \
    for msi in tcltk lib; do \
        echo "  Extracting ${msi}.msi..." && \
        cd /tmp/msi_out && msiextract /tmp/${msi}.msi 2>&1; \
    done && \
    cp -r /tmp/msi_out/* "$PYDIR/" && \
    test -f "$PYDIR/DLLs/_tkinter.pyd" && \
    test -f "$PYDIR/Lib/tkinter/__init__.py" && \
    rm -rf /tmp/*.msi /tmp/msi_out && \
    echo "--- tkinter installed ---"

ENV TCL_LIBRARY=C:\\Python311\\tcl\\tcl8.6
ENV TK_LIBRARY=C:\\Python311\\tcl\\tk8.6

RUN echo "--- Installing pdfplumber and pyinstaller ---" && \
    wine C:/Python311/python.exe -m pip install --no-cache-dir \
        pdfplumber pyinstaller 2>&1 && \
    while pgrep wineserver > /dev/null; do sleep 1; done && \
    echo "--- Python packages installed ---"

WORKDIR /src
