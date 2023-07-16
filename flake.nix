{
  description = "my project description";

  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.poetry2nixFlake.url = "github:nix-community/poetry2nix/master";

  outputs = { self, nixpkgs, flake-utils, poetry2nixFlake }:
    flake-utils.lib.eachDefaultSystem
      (system:
        let pkgs = nixpkgs.legacyPackages.${system}; in
        {
          devShells.default = import ./shell.nix { pkgs = pkgs // { poetry2nix = poetry2nixFlake.legacyPackages.${system}; }; };
        }
      );
}