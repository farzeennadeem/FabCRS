# FabCRS
This is a dummy example plugin for FabSim3. It is meant to showcase a minimal implementation for a FabSim3 plugin.

## Installation
Simply type `fabsim localhost install_plugin:FabCRS` anywhere inside your FabSim3 install directory.

## Testing
1. To run a dummy job, type `fabsim localhost dummy:dummy_test`.

## Explanation of files
* FabDummy.py - main file containing the ```fabsim localhost dummy``` command implementation.
* config_files/dummy_test - directory containing input data for the dummy command.
* templates/dummy - template file for running the dummy command on the remote machine.

## Detailed Examples

### Executing a single job on localhost

1. To run a dummy job, type `fabsim localhost dummy:dummy_test`. This does the following:
  - Copy your job input, which is in `plugins/FabDummy/config_files/dummy_test`, to the remote location specified in the variable `remote_path_template` in `deploy/machines.yml`.
  - Copy the input to the remote results directory.
  - Start the remote job.
2. If your job runs without a scheduler (normally the case when running on localhost), you can simply wait for it to finish, or cancel the job using Ctrl+C.
3. After the job has finished, the terminal becomes available again, and a message is printing indicating where the output data resides remotely.
4. You can fetch the remote data using `fabsim localhost fetch_results`, and then use it as you see fit! Local results are typically locations in the `results/` subdirectory.


### Executing a single job on a remote host

1. Ensure the host is defined in machines.yml, and the user login information in `deploy/machines_user.yml`.
2. To run a dummy job, type `fabsim <machine name> dummy:dummy_test`. This does the following:
  - Copy your job input, which is in `plugins/FabDummy/config_files/dummy_test`, to the remote location specified in the variable `remote_path_template` in `deploy/machines.yml` (not it will substitute in machine-specific variables provided in the same file).
  - Copy the input to the remote results directory.
  - Start the remote job.
3. Your job now likely runs using a scheduler, so your terminal becomes available again. Use `fabsim <machine> stat` to track its submission status, or `fabsim <machine> monitor` to poll periodically for the job status.
4. If the stat or monitor commands do not show your job being listed, then your job has finished (successfully or unsuccessfully).
5. You can then fetch the remote data using `fabsim localhost fetch_results`, and investigate the output as you see fit. Local results are typically locations in the `results/` subdirectory.


### Executing an ensemble job on a remote host

1. Ensure the host is defined in machines.yml, and the user login information in `deploy/machines_user.yml`.
2. To run a dummy job, type `fabsim <machine name> dummy_ensemble:dummy_test`. This does the following:
  a. Copy your job input, which is in `plugins/FabDummy/config_files/dummy_test`, to the remote location specified in the variable `remote_path_template` in `deploy/machines.yml` (not it will substitute in machine-specific variables provided in the same file).
  b. Copy the input to the remote results directory.
  c. Substitute in the first input file in `plugins/FabDummy/config_files/dummy_test/SWEEP`, renaming it in-place to dummy.txt for the first ensemble run.
  d. Start the remote job.
  e. Repeat b-d for each other base-level file or directory in `plugins/FabDummy/config_files/dummy_test/SWEEP`.
3. Use `fabsim <machine> job_stat` to track the submission status of your jobs, or `fabsim <machine> monitor` to poll periodically for the job status.
4. If the stat or monitor commands do not show any jobs being listed, then all your job has finished (successfully or unsuccessfully).
5. You can then fetch the remote data using `fabsim localhost fetch_results`, and investigate the output as you see fit. Local results are typically locations in the various `results/` subdirectories.

### Executing an ensemble job on a remote host with replicas

Replicas are jobs that have identical inputs and configurations. Their outputs may be different however, e.g. due to stochastic or non-deterministic aspects of the simulation algorithm. To run each instance of the ensembles with *N* replicated instances, add a `replicas=<N>` to your command. For example, to run a dummy ensemble with 5 replicas each, just use `fabsim <machine name> dummy_ensemble:dummy_test,replicas=5`.