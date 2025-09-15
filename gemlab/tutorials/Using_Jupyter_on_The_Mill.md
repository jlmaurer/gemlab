# Using Jupyter on The Mill
The Mill is S&T's supercomputer facility. 
You can run Jupyter Notebooks directly on The Mill, but by default it does not use your conda environments. The instructions below are for running notebooks within a conda environment. 
The example uses RAiDER as the example package, but any other package can be subsituted. 

## Instructions
Go the The Mill website, and select the "Mill Shell Access" option. That will open a terminal. Type "sinteractive" and hit enter until it comes up with a screen that has a bunch of options on it. Then hit ctrl + c to open a new terminal. 

In the new terminal, you'll need to create a new RAiDER environment if you have not already done so. You can use the following command to do that: 
conda env create --name RAiDER  -c conda-forge raider

Once you have done that, then run the following command: 
python -m ipykernel install --user --name=RAiDER

Now go back to The Mill main page, and open up the Jupyter notebook option. Maybe change the memory to 16 GB or something like that, and then launch Jupyter. That will bring up a page that will eventually say "Go to Jupyter" or similar, which you can click to launch the notebook browser. I should say you'll want to have the RAiDER example notebooks already uploaded to your Mill directory before this. 

Open up the tutorial notebook, and at the top right corner you should see button with "Kernel". Click the Kernal button and you should see a dropdown to select a kernel. Select the "RAiDER" kernel. 

Go through and run the notebook! Once you've run through it to see the examples, you can start modifying the commands / config files to your area. 

When you are done, you can type ctrl+d and then "exit" and enter to close the terminal. 

