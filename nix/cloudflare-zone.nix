{ config, lib, uuid, name, ... }:

with lib;
with (import ./lib.nix lib);

let
  record = types.submodule ({ config, name, ... }: {
    options = {
      content = mkOption {
        type = types.either types.str (resource "machine");
        apply = x: if builtins.isString x then x else "res-" + x._name;
        description = "The record contents";
      };
      proxied = mkOption {
        default = false;
        type = types.bool;
        description = "Whether to proxy the record through cloudflare";
      };
    };
  });
in
{

  options = {
    zone = mkOption {
      default = "${name}";
      type = types.str;
      description = "The zone to work with";
    };
    email = mkOption {
      type = types.str;
      description = "The email of the cloudflare account";
    };
    token = mkOption {
      type = types.str;
      description = "The token of the cloudflare account";
    };
    records = mkOption {
      type = types.attrsOf (types.attrsOf (types.listOf record));
      description = "The records to set";
    };
  };

}
