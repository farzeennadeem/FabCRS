# -*- coding: utf-8 -*-
#
# This source file is part of the FabSim software toolkit, which is distributed under the BSD 3-Clause license.
# Please refer to LICENSE for detailed information regarding the licensing.
#
# This file contains FabSim definitions specific to FabDummy.

try:
    from fabsim.base.fab import *
    from fabsim.VVP import vvp
except ImportError:
    from base.fab import * # pyright: ignore[reportMissingImports]

# Add local script, blackbox and template path.
add_local_paths("FabCRS")

@task
@load_plugin_env_vars("FabCRS")
def run_crs(config, **args):
    """
    Run a CRS simulation using dummy job script.
    Usage: 
        fabsim localhost run_crs:<scenario>

        E.g. fabsim localhost run_crs:http_flood
    """
    update_environment(args)
    with_config(config)
    execute(put_configs, config)
    job(dict(script='crs_run', job_wall_time='0:15:0', memory='2G'), args)

@task
@load_plugin_env_vars("FabCRS")
def crs_generate_dashboard(config, **args):
    """
    Generate dashboard.html for a specific run folder.
    Usage:
      fabsim localhost crs_generate_dashboard:<group>,run=<run_folder>

      E.g. fabsim localhost crs_generate_dashboard:http_flood_localhost_1,run=run_DD_MM_YYYY_HHMMSS
    """
    update_environment(args)

    run_folder = args.get("run")
    if not run_folder:
        raise Exception("Please provide run=<run_folder>, e.g. run=run_DD_MM_YYYY_HHMMSS")

    scenario_parts = config.split("_")
    if len(scenario_parts) >= 3:
        scenario_name = "_".join(scenario_parts[:-2])
    else:
        scenario_name = config

    with_config(scenario_name)

    args["results_group"] = config
    args["run"] = run_folder

    print("DEBUG kwargs args =", args)

    #DONT put_configs here as we are reading existing results
    job(dict(script="crs_db", job_wall_time="0:15:0", memory="2G"), args)

@task
@load_plugin_env_vars("FabCRS")
def crs_secure_advisor(config, **args):
    """
    Run SecureAdvisor to suggest fixes for a specific run.
    Usage: 
        fabsim localhost crs_secure_advisor:<group>,run=<run_folder>

        E.g. fabsim localhost crs_secure_advisor:http_flood_localhost_1,run=run_DD_MM_YYYY_HHMMSS
    """
    update_environment(args)
    
    run_folder = args.get("run")
    if not run_folder:
        raise Exception("Please provide run=<run_folder>")
    
    scenario_parts = config.split("_")
    if len(scenario_parts) >= 3:
        scenario_name = "_".join(scenario_parts[:-2])
    else:
        scenario_name = config

    with_config(scenario_name)

    args["results_group"] = config
    args["run"] = run_folder

    # Execute the template
    job(dict(script="crs_secureadvisor", job_wall_time="0:05:0", memory="1G"), args)

# -----------------DUMMY TASK TEMPLATES-------------------------
@task
def start(config, **args):
    """Submit a Dummy job to the remote queue.
    The job results will be stored with a name pattern as defined in the environment,
    e.g. cylinder-abcd1234-legion-256
    config : config directory to use to define input files, e.g. config=cylinder
    Keyword arguments:
            cores : number of compute cores to request
            images : number of images to take
            steering : steering session i.d.
            wall_time : wall-time job limit
            memory : memory per node
    """
    update_environment(args)
    with_config(config)
    execute(put_configs, config)
    job(dict(script='CRS_test', job_wall_time='0:15:0', memory='2G'), args)

@task
def dummy(config, **args):
    """Submit a Dummy job to the remote queue.
    The job results will be stored with a name pattern as defined in the environment,
    e.g. cylinder-abcd1234-legion-256
    config : config directory to use to define input files, e.g. config=cylinder
    Keyword arguments:
            cores : number of compute cores to request
            images : number of images to take
            steering : steering session i.d.
            wall_time : wall-time job limit
            memory : memory per node
    """
    update_environment(args)
    with_config(config)
    execute(put_configs, config)
    job(dict(script='dummy', job_wall_time='0:15:0', memory='2G'), args)


@task
def dummy_ensemble(config="dummy_test", **args):
    """
    Submits an ensemble of dummy jobs.
    One job is run for each file in <config_file_directory>/dummy_test/SWEEP.
    """

    path_to_config = find_config_file_path(config)
    print("local config file path at: %s" % path_to_config)
    sweep_dir = path_to_config + "/SWEEP"
    env.script = 'dummy'
    env.input_name_in_config = 'dummy.txt'
    with_config(config)
    run_ensemble(config, sweep_dir, **args)


@task
def lammps_dummy(config, **args):
    """Submit a LAMMPS job to the remote queue.
    The job results will be stored with a name pattern as defined in the environment,
    e.g. cylinder-abcd1234-legion-256
    config : config directory to use to define geometry, e.g. config=lamps_lj_liquid
    Keyword arguments:
            cores : number of compute cores to request
            images : number of images to take
            steering : steering session i.d.
            wall_time : wall-time job limit
            memory : memory per node
    """
    with_config(config)
    execute(put_configs, config)
    job(dict(script='lammps', wall_time='0:15:0', lammps_input="in.CG.lammps"), args)


def compare_dummy_results(results_dir, sif_dir, verbose=True, **kwargs):
    if verbose:
        print("COMPARE DUMMY RESULTS")
        print("test subject source: {}/out.txt".format(results_dir))
        print("SIF source: {}/out.txt".format(sif_dir))

    out_rf = open("{}/out.txt".format(results_dir),'r')
    out_sf = open("{}/out.txt".format(sif_dir),'r')
    
    rf_content = out_rf.readlines()
    sf_content = out_sf.readlines()

    rf = 0.0
    sf = 0.000001
    for l in rf_content:
        rf = float(l)

    for l in sf_content:
        sf = float(l)

    if verbose:
        print("VVP test subject result {}, VVP stable intermediate formresult {}".format(rf,sf))

    return(abs(rf-sf)/sf)


def dummy_avg(scores, **kwargs):
  return scores


@task
def dummy_sif(config, testing_template='dummy_to_be_tested', skip_runs=False, **args):

  with_config(config)
  execute(put_configs, config)
  job(dict(script='dummy_sif', label='sif', wall_time='0:15:0'), args)
  job(dict(script=testing_template, label='test_subject', wall_time='0:15:0'), args)

  # if not run locally, wait for runs to complete
  update_environment()
  if env.host != "localhost":
    wait_complete("")
  if skip_runs:
    env.config = "validation"

  fetch_results()

  results_dir = template(env.job_name_template)
  print(results_dir)

  scores = vvp.sif_vvp("{}/test_subject_{}".format(env.local_results, results_dir), "{}/sif_{}".format(env.local_results, results_dir), compare_dummy_results, dummy_avg)

  print("SCORES:",scores)


@task
def print_dummy_output(results_dir):
    update_environment()
    # Open the file in read mode
    file_path = f"{env.local_results}/{results_dir}/out.txt"
    print(file_path)

    try:
        with open(file_path, 'r') as file:
            # Read the content of the file
            file_content = file.read()

            # Print the content
            # We print to stderr, so that the output appears in a Jupyter notebook.
            print("File Content:\n", file_content, file=sys.stderr)

    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

