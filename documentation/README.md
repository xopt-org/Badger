# Badger Homepage

Any PR that merged into master branch of this repo will trigger an auto-deployment to the [Badger homepage](https://xopt-org.github.io/Badger/).

This repo could be merged into [Badger core repo](https://github.com/xopt-org/Badger) soon.

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
