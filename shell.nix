{ pkgs ? import <nixpkgs> { } }:
let
  pypkgs-build-requirements = {
    annotated-types = [ "hatchling" ];
    async-timeout = [ "hatchling" ];
    attrs = [ "hatchling" "hatch-fancy-pypi-readme" "hatch-vcs" ];
    nvidia-ml-py = [ "setuptools" ];
    oauthlib = [ "setuptools" ];
    opencensus-context = [ "setuptools" ];
    strenum = [ "pytest-runner" ];
    ray = [ "setuptools" ];
    gpustat = [ "setuptools" "setuptools-scm" ];
    pydantic = [ "hatchling" "hatch-fancy-pypi-readme" ];
    urllib3 = [ "hatchling" ];
    opencensus = [ "setuptools" ];
  };
  p2n-overrides = pkgs.poetry2nix.defaultPoetryOverrides.extend (self: super:
    builtins.mapAttrs
      (package: build-requirements:
        (builtins.getAttr package super).overridePythonAttrs (old: {
          buildInputs = (old.buildInputs or [ ]) ++ (builtins.map (pkg: if builtins.isString pkg then builtins.getAttr pkg super else pkg) build-requirements);
        })
      )
      pypkgs-build-requirements
  );
in
let
  myAppEnv = pkgs.poetry2nix.mkPoetryEnv {
    projectDir = ./.;
    editablePackageSources = {
      my-app = ./acto;
    };
    overrides = p2n-overrides.extend (self: super: {
      rpds-py = super.rpds-py.overridePythonAttrs (old: rec {
        src = pkgs.fetchFromGitHub {
          owner = "crate-py";
          repo = "rpds";
          rev = "v${old.version}";
          sha256 = "sha256-DJPYxJ1gJFmRy+a8KmR1H6tFHKTyd0D5PDD30iH7z1g=";
        };
        cargoDeps = pkgs.rustPlatform.importCargoLock {
          lockFile = "${src.out}/Cargo.lock";
        };
        nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [
          pkgs.rustPlatform.cargoSetupHook
          pkgs.rustPlatform.maturinBuildHook
        ];
      });
      ray = super.ray.overrideAttrs (old: rec {
        postInstall = let patchFile = ./ray-dashboard.patch; in (old.postInstall or "") + ''
            find $out/${super.python.sitePackages}/ray -name metrics_head.py | xargs -I {} sh -c "patch {} < ${patchFile}"
            find $out/${super.python.sitePackages}/ray -name 'metrics_head.*.pyc' -type f -delete
        '';
      });
    });
  };
in
(myAppEnv.override (args: { ignoreCollisions = true; })).env.overrideAttrs (oldAttrs: {
  buildInputs = with pkgs; [go kubectl kind poetry];
})