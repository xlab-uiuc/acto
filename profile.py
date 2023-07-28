"""Variable number of nodes in a lan. You have the option of picking from one
of several standard images we provide, or just use the default (typically a recent
version of Ubuntu). You may also optionally pick the specific hardware type for
all the nodes in the lan.

Instructions:
Wait for the experiment to start, and then log into one or more of the nodes
by clicking on them in the toplogy, and choosing the `shell` menu option.
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
bootstrap_script_rel_path = "scripts/cl_bootstrap.sh"
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

# Acto bootstrap
bootstrap_script_path = os.path.join(cl_repo_path, bootstrap_script_rel_path)
node.addService(pg.Execute(shell="bash", command=bootstrap_script_path))

# Print the RSpec to the enclosing page.
pc.printRequestRSpec(request)
