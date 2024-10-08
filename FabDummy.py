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
    from base.fab import *

# Add local script, blackbox and template path.
add_local_paths("FabDummy")


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
