import os
import sys
import modules.scripts as scripts
import gradio as gr
import math
import random
from modules.processing import Processed, process_images, fix_seed
from modules.shared import opts, cmd_opts, state


class Script(scripts.Script):
    def title(self):
        return "Seed Travel Test"

    def show(self, is_img2img):
        return True

    def ui(self, is_img2img):
        def gr_show(visible=True):
            return {"visible": visible, "__type__": "update"}

        def change_visibility(show):
            return {comp: gr_show(show) for comp in seed_travel_extra}

        seed_travel_extra = []

        steps = gr.Number(label='Steps', value=7)
        seed_count = gr.Number(label='Number of Random Seeds', value=10)
        seed_travel_toggle_extra = gr.Checkbox(label='Show extra settings', value=False)

        with gr.Row(visible=False) as seed_travel_extra_row:
            seed_travel_extra.append(seed_travel_extra_row)
            with gr.Box() as seed_travel_box1:
                rnd_seed = gr.Checkbox(label='Use Random Starting Seeds', value=False)
                unsinify = gr.Checkbox(label='Reduce effect of sin() during interpolation', value=False)
                show_images = gr.Checkbox(label='Show generated images in ui', value=True)
            with gr.Box() as seed_travel_box2:
                save_video = gr.Checkbox(label='Save results as video', value=False)
                video_fps = gr.Number(label='Frames per second', value=30)

        seed_travel_toggle_extra.change(change_visibility, show_progress=False, inputs=[seed_travel_toggle_extra], outputs=seed_travel_extra)        

        return [rnd_seed, seed_count, steps, unsinify, save_video, video_fps, seed_travel_toggle_extra, show_images]

    def get_next_sequence_number(path):
        from pathlib import Path
        """
        Determines and returns the next sequence number to use when saving an image in the specified directory.
        The sequence starts at 0.
        """
        result = -1
        dir = Path(path)
        for file in dir.iterdir():
            if not file.is_dir(): continue
            try:
                num = int(file.name)
                if num > result: result = num
            except ValueError:
                pass
        return result + 1

    def run(self, p, rnd_seed, seed_count, steps, unsinify, save_video, video_fps, seed_travel_toggle, show_images):
        initial_info = None
        images = []

        if rnd_seed and (not seed_count or int(seed_count) < 2):
            print(f"You need at least 2 random seeds.")
            return Processed(p, images, p.seed)

        if not rnd_seed and int(p.seed) == -1:
            print(f"Must define starting seed.")
            return Processed(p, images, p.seed)

        if not save_video and not show_images:
            print(f"Nothing to do. You should save the results as a video or show the generated images.")
            return Processed(p, images, p.seed)

        if save_video:
            import numpy as np
            try:
                import moviepy.video.io.ImageSequenceClip as ImageSequenceClip
            except ImportError:
                print(f"moviepy python module not installed. Will not be able to generate video.")
                return Processed(p, images, p.seed)

        # Custom seed travel saving
        travel_path = os.path.join(p.outpath_samples, "travels")
        os.makedirs(travel_path, exist_ok=True)
        travel_number = Script.get_next_sequence_number(travel_path)
        travel_path = os.path.join(travel_path, f"{travel_number:05}")
        p.outpath_samples = travel_path

        # Force Batch Count to 1.
        p.n_iter = 1

        # Destination Seeds
        dest_seeds = []          
        dest_s = 0          
        while (dest_s < seed_count):
            dest_seeds.append(random.randint(0,2147483647))
            print(dest_seeds)
            dest_s = dest_s + 1
        
        # Random seeds
        if rnd_seed == True:
            start_seeds = []          
            start_s = 0          
            while (start_s < seed_count):
                start_seeds.append(random.randint(0,2147483647))
                print(start_seeds)
                start_s = start_s + 1
        # Manual seeds        
        else:
            start_seeds = []          
            start_s = 0          
            while (start_s < seed_count):
                start_seeds.append(p.seed)
                print(start_seeds)
                start_s = start_s + 1
        
        total_images = (int(steps) * len(dest_seeds))
        print(f"Generating {total_images} images.")

        # Set generation helpers
        state.job_count = total_images

        for i in range(len(start_seeds)):
            p.seed = start_seeds[i] #Set seed to current start seed.
            p.subseed = dest_seeds[i]  #Set variation seed to dest seed.
            fix_seed(p)#Some kind of seed processing?
            start_seeds[i] = p.seed #Save seed as is in case of changes
            if i < len(start_seeds): dest_seeds[i] = p.subseed #Possibly tied to the saving of seeds still?
            
            numsteps = int(steps)
            for i in range(numsteps):
                if unsinify:
                    x = float(i/float(steps))
                    p.subseed_strength = x + (0.1 * math.sin(x*2*math.pi))
                else:
                    p.subseed_strength = float(i/float(steps))
                proc = process_images(p)
                if initial_info is None:
                    initial_info = proc.info
                images += proc.images

        if save_video:
            clip = ImageSequenceClip.ImageSequenceClip([np.asarray(i) for i in images], fps=video_fps)
            clip.write_videofile(os.path.join(travel_path, f"travel-{travel_number:05}.mp4"), verbose=False, logger=None)

        processed = Processed(p, images if show_images else [], p.seed, initial_info)

        return processed

    def describe(self):
        return "Travel between two (or more) seeds and create a picture at each step."