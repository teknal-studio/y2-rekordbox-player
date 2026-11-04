# Toolchain for the Y2 Rockbox Android native build. NDK r10e is x86_64 only.
FROM --platform=linux/amd64 ubuntu:22.04
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc-multilib perl python3 unzip zip curl ca-certificates \
    file e2fsprogs android-sdk-libsparse-utils dos2unix bzip2 xz-utils \
    libsdl2-dev openjdk-8-jdk-headless zlib1g libc++1
RUN curl -fsSL -o /tmp/ndk.zip https://dl.google.com/android/repository/android-ndk-r10e-linux-x86_64.zip \
    && mkdir -p /opt && unzip -q /tmp/ndk.zip -d /opt && rm /tmp/ndk.zip
ENV ANDROID_NDK_PATH=/opt/android-ndk-r10e
WORKDIR /work
# Java side: SDK platform plus 64-bit build tools, since Rosetta can't run the 32-bit r19 aapt.
RUN curl -fsSL -o /tmp/p.zip https://dl.google.com/android/repository/android-19_r04.zip \
    && curl -fsSL -o /tmp/b.zip https://dl.google.com/android/repository/build-tools_r23.0.3-linux.zip \
    && mkdir -p /opt/sdk/platforms /opt/sdk/build-tools \
    && unzip -q /tmp/p.zip -d /opt/sdk/platforms && mv /opt/sdk/platforms/android-4.4.2 /opt/sdk/platforms/android-19 \
    && unzip -q /tmp/b.zip -d /opt/sdk/build-tools && mv /opt/sdk/build-tools/android-6.0 /opt/sdk/build-tools/23.0.3 \
    && rm /tmp/p.zip /tmp/b.zip
RUN curl -fsSL -o /tmp/b.zip https://dl.google.com/android/repository/build-tools_r28.0.3-linux.zip \
    && unzip -q /tmp/b.zip -d /opt/sdk/build-tools && mv /opt/sdk/build-tools/android-9 /opt/sdk/build-tools/28.0.3 && rm /tmp/b.zip
