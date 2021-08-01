FROM debian:stable-slim
# FROM raspbian/bullseye
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get full-upgrade -y
RUN apt-get update -y
RUN apt-get install software-properties-common -y
RUN apt-get install apt-utils -y
# https://www.raspbian.org/RaspbianMirrors
# https://www.debian.org/mirror/list
# RUN apt-get install netselect-apt -y
# RUN add-apt-repository 'deb http://debian.csail.mit.edu stable/main armhf'
RUN apt-get install gcc -y
RUN apt-get install nano -y
RUN apt-get install tar -y
RUN apt-get install bash -y
RUN apt-get install sudo -y
RUN apt-get install openssl -y
RUN apt-get install git -y
RUN apt-get install make -y
RUN apt-get install cmake -y
RUN apt-get install gfortran -y
RUN apt-get install pkg-config -y
RUN apt-get install wget -y
RUN apt-get install curl -y
RUN apt-get install unzip -y
RUN apt-get install net-tools -y
RUN apt-get install iproute2 -y
RUN apt-get install iputils-ping -y
RUN apt-get install tzdata -y

RUN apt-get install python-pip -y
RUN apt-get install python3-pip -y
RUN apt-get install python3-venv -y
RUN apt-get install build-essential -y
RUN apt-get install python3-dev -y
RUN apt-get install python3-setuptools -y
RUN apt-get install python3-smbus -y
RUN apt-get install python3-numpy -y
RUN apt-get install python3-scipy -y
RUN apt-get install libncursesw5-dev -y
RUN apt-get install libgdbm-dev -y
RUN apt-get install libc6-dev -y
RUN apt-get install zlib1g-dev -y
RUN apt-get install libsqlite3-dev -y
RUN apt-get install tk-dev -y
RUN apt-get install libssl-dev -y
RUN apt-get install openssl -y
RUN apt-get install libffi-dev -y
RUN apt-get install libbz2-dev -y
RUN apt-get install libreadline-dev -y
RUN apt-get install llvm -y
RUN apt-get install libncurses5-dev -y
RUN apt-get install xz-utils -y
RUN apt-get install tk-dev -y
RUN apt-get install libxml2-dev -y
RUN apt-get install libxmlsec1-dev -y
RUN apt-get install liblzma-dev -y
RUN apt-get install libatlas-base-dev -y
RUN apt-get install libopenjp2-7 -y
RUN apt-get install libtiff5 -y
RUN apt-get install apt-transport-https -y
RUN apt-get install ca-certificates  -y
RUN update-ca-certificates -f
RUN mkdir -p /etc/pki/tls/certs
RUN cp /etc/ssl/certs/ca-certificates.crt /etc/pki/tls/certs/ca-bundle.crt

ENV TZ="US/Eastern"
RUN echo "US/Eastern" > /etc/timezone
RUN dpkg-reconfigure -f noninteractive tzdata
ARG USERNAME="morphs"
ARG PASSWORD="asdfasdf"
RUN useradd -m $USERNAME -p $PASSWORD -s "/bin/bash"
RUN mkdir -p /home/$USERNAME
RUN chown -R $USERNAME:$USERNAME /home/$USERNAME
RUN usermod -aG sudo $USERNAME
RUN echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER $USERNAME
WORKDIR /home/$USERNAME
RUN echo 'cacert=/etc/ssl/certs/ca-certificates.crt' > ~/.curlrc
RUN mkdir -p /home/$USERNAME/FRAME_CONSUMER
RUN sudo chown -R $USERNAME:$USERNAME /home/$USERNAME/FRAME_CONSUMER
COPY . /home/$USERNAME/FRAME_CONSUMER
RUN sudo chown -R $USERNAME:$USERNAME /home/$USERNAME/FRAME_CONSUMER

# https://github.com/pyenv/pyenv
# https://gist.github.com/jprjr/7667947

ENV PYTHON_VERSION 3.7.3
RUN git clone https://github.com/pyenv/pyenv.git /home/$USERNAME/.pyenv
ENV PYENV_ROOT /home/$USERNAME/.pyenv
ENV PATH $PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH
RUN /home/$USERNAME/.pyenv/bin/pyenv install $PYTHON_VERSION
RUN /home/$USERNAME/.pyenv/bin/pyenv global $PYTHON_VERSION
RUN /home/$USERNAME/.pyenv/bin/pyenv rehash

WORKDIR /home/$USERNAME/FRAME_CONSUMER
RUN ./install_venv.sh
# ENV DISPLAY=:10.0
# ENTRYPOINT [ "/bin/bash" ]
ENTRYPOINT [ "/usr/bin/python3" , "/home/morphs/FRAME_CONSUMER/main.py" ]