# Badger Homepage

The Badger Homepace hosts the Badger documentation, and can be accessed at: [https://xopt-org.github.io/Badger/](https://xopt-org.github.io/Badger/).

Any new additions or edits to Badger's documentation can be made here in the Badger repo's `/documentation` folder.
The homepage source must build successfully on each PR before it can be merged into main.
Then once merged the main branch will trigger an automatic deployment of the homepage website.

### Building Homepage Locally

After making changes to the Badger Homepage source, you can test things out by building it locally:

1. Install nodejs and npm (on linux these are probably in your distribution's package manager, for ex. on ubuntu try: `sudo apt install -y nodejs npm`)
2. `cd Badger/documentation`
3. `npm install`
4. `npm run build` (if this fails there are issues with your changes!)
5. `npm run serve`
5. Now open an internet-broweser to address `http://localhost:3000` to view your locally built version of the homepage!


### Notes on creating highlighted images

When making an image that highlights a particular portion of the GUI, this process was used for most images:

1. Load the base image in GIMP - usually `static/img/gui/run_1.png`.
2. Make a rectangular selection around the UI element with antialiasing enabled and rounded corners set to 6px.
3. Invert the selection. (Select -> Invert)
4. Set saturation to 0.25. (Colors -> Saturation...)
5. Invert the selection. (Select -> Invert)
6. Create a stroke from the selection. (Edit -> Stroke Selection...)
   - Use Line mode.
   - Set the color to `#f83232`.
   - Enable antialiasing.
   - Set width to 6px.
   - Use "Round" join style.
7. If adding numbers to denote different parts of the image, use Noto Sans Regular font. A size of 72px was used for most images.
