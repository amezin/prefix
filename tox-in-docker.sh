#!/bin/bash

set -e

message() {
    echo "$(tput setaf 2)"\> "$@""$(tput sgr0)"
}

srcdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
workdir="${srcdir}/.tox/docker"
mkdir -pv "${workdir}"

remove_container() {
    if [[ -e "${workdir}/container-id" ]]; then
        message Deleting old container "$(cat "${workdir}/container-id")"
        docker rm -f "$(cat "${workdir}/container-id")" || true
        rm -v "${workdir}/container-id"
    fi
}

remove_container

remove_old_image() {
    if [[ -e "${workdir}/image-id.old" ]]; then
        if ! diff -q "${workdir}/image-id" "${workdir}/image-id.old"; then
            message Removing old image "$(cat "${workdir}/image-id.old")"
            docker rmi "$(cat "${workdir}/image-id.old")" || true
        fi
        rm -v "${workdir}/image-id.old"
    fi
}

if [[ -e "${workdir}/image-id" ]]; then
    remove_old_image
    mv -v "${workdir}/image-id" "${workdir}/image-id.old"
fi

message Building image
docker build --iidfile "${workdir}/image-id" -t "prefix-tox:base" "${srcdir}"

remove_old_image

message Running image "$(cat "${workdir}/image-id")"
if ! docker run -t --cidfile "${workdir}/container-id" -v "${srcdir}:${srcdir}" -w "${srcdir}" "$(cat "${workdir}/image-id")" tox --workdir "${workdir}" "$@"; then
    if [[ -n "${CI}" ]]; then
        exit 1
    fi

    message Failed, attaching to "$(cat "${workdir}/container-id")"

    temp_image="$(docker commit "$(cat "${workdir}/container-id")" prefix-tox:failed)"
    echo "${temp_image}" > "${workdir}/image-id.old"
    message Saved container state as image ${temp_image}

    remove_container

    message Running ${temp_image}
    docker run -ti --cidfile "${workdir}/container-id" -v "${srcdir}:${srcdir}" "${temp_image}" /bin/bash
fi
