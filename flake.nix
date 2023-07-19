{
  description = "my project description";

  inputs.flake-utils.url = "github:numtide/flake-utils/919d646de7be200f3bf08cb76ae1f09402b6f9b4";
  inputs.poetry2nixFlake.url = "github:nix-community/poetry2nix/e7a88dfc2c5aa0c660a3ec4661a695c1c2380a8a";

  outputs = { self, nixpkgs, flake-utils, poetry2nixFlake }:
    flake-utils.lib.eachDefaultSystem
      (system:
        let pkgs = nixpkgs.legacyPackages.${system}; in
        {
          devShells.default = import ./shell.nix { pkgs = pkgs // { poetry2nix = poetry2nixFlake.legacyPackages.${system}; }; };
        }
      );
}