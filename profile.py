"""Profile for running Acto on CloudLab. There is one single physical node. The
OS image is hardwired to Ubuntu 20.04. The hardware type is configurable by you
during the instantiation stage. We recommend `c6420` for the best results (the
default), but if that's not currently available, you may also select another
type, e.g. `c8220`.

Instructions:
Wait for the experiment to start, and then log into the node by either way:

1. (Web-based) clicking on it in the toplogy, and choosing the `shell` menu
option.
2. (Terminal-based) the SSH command you need to login will be provided to you on
the web dashboard, in the form of `ssh <user>@<node>.<cluster>.cloudlab.us`.

Use `sudo` to run root commands.
"""

# Import the Portal object.
import geni.portal as portal
# Import the ProtoGENI library.
import geni.rspec.pg as pg
# Emulab specific extensions.
import geni.rspec.emulab as emulab

import os

cl_repo_path              = "/local/repository/"
startup_script_rel_path = "scripts/cloudlab_startup_run_by_geniuser.sh"
hostname                  = "acto-physical-worker-0"

# Create a portal context, needed to defined parameters
pc = portal.Context()

# Create a Request object to start building the RSpec.
request = pc.makeRequestRSpec()

# Fixate parameters
osImage = 'urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU20-64-STD'

# Except this one, in case c6420 is not available
# Optional physical type for all nodes.
pc.defineParameter("phystype",  "Optional physical node type",
                   portal.ParameterType.STRING, "c6420",
                   longDescription="Specify a single physical node type (pc3000,d710,etc) " +
                   "instead of letting the resource mapper choose for you.")

# Retrieve the values the user specifies during instantiation.
params = pc.bindParameters()

# Check parameter validity.
pc.verifyParameters()

node = request.RawPC(hostname)
node.disk_image = osImage
node.hardware_type = params.phystype

# Acto startup
startup_script_path = os.path.join(cl_repo_path, startup_script_rel_path)
node.addService(pg.Execute(shell="bash", command=startup_script_path))

# Print the RSpec to the enclosing page.
pc.printRequestRSpec(request)
