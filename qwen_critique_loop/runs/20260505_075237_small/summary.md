# Critique Loop Run — 2026-05-05T08:56:30

**Input:** `/Users/michaellinares/Documents/imgSequel/qwen_critique_loop/small.JPG`

**Original size:** 300 x 400

**Diffusion model:** `SG161222/RealVisXL_V4.0`

**VLM:** `mlx-community/Qwen2.5-VL-7B-Instruct-4bit`

**Mode:** img2img (strength=0.55)

**Rounds:** 5

---

## Original photograph — technical signature

```
CAMERA_FORMAT: 35mm full-frame
ERA: 2005-2010 digital point-and-shoot
FILM_OR_DIGITAL: digital
FOCAL_LENGTH_MM: 50
APERTURE: f/2.8
SHUTTER_FEEL: crisp
ISO_FEEL: medium
WHITE_BALANCE_K: 5500
COLOR_GRADE: neutral
CONTRAST: medium contrast lifted blacks
SATURATION: natural
GRAIN_OR_NOISE: none
SHARPNESS: natural
DEPTH_OF_FIELD: medium
LIGHTING_SOURCE: overhead fluorescent
LIGHTING_QUALITY: soft
COMPOSITION: subject centered, slight tilt, background frames subject
SUBJECT: elderly person wearing red coat and hood, holding object in hand
SETTING: indoor space with framed artwork on wall
MOOD: candid, everyday moment
NOTABLE_IMPERFECTIONS: slight motion blur on hand, JPEG artifacts in shadows
```

**Scoreboard:** sequel 1 · original 4 · tie 0

---

## Round 1

**Input image:** `/Users/michaellinares/Documents/imgSequel/qwen_critique_loop/runs/20260505_075237_small/original.jpg`

**Sequel image:** `/Users/michaellinares/Documents/imgSequel/qwen_critique_loop/runs/20260505_075237_small/round_01/sequel.png`

### Critique

### Composition
The subject is placed slightly off-center, adhering to the rule of thirds, which is a good starting point. However, the leading lines are not effectively utilized, as the subject does not naturally guide the viewer's eye through the frame. The framing could be tighter, focusing more on the subject and less on the background, which includes framed pictures. The balance appears slightly off due to the subject's posture and the uneven distribution of the background elements. Negative space could be better managed to enhance the subject's prominence. The subject placement is good but could be improved to better align with the rule of thirds and to create a more dynamic composition.

### Lighting
The lighting appears to be soft and diffused, possibly from an interior source. The shadows are soft and not harsh, suggesting the use of a diffuser or indirect light. The color temperature seems balanced, with no strong偏冷 or偏暖 tones. The contrast ratios appear reasonable, with the subject's red jacket standing out against the more muted background. The time of day is not definitively clear, but the lighting suggests it might be taken indoors with artificial light.

### Exposure & Tonality
The exposure seems well-balanced, with no significant clipping in highlights or shadows. The midtone separation is good, allowing for clear detail in both the subject and the background. The overall density of the image appears appropriate for the subject matter, with the red jacket drawing the eye without overwhelming the frame.

### Color
The color palette is consistent, with the red jacket being the dominant color and the background being more subdued. The saturation of the red is high, which is intentional and works well to make the subject stand out. The relationships between colors are harmonious, with the red jacket complementing the neutral tones of the background. There is a good level of color consistency, and the dissonance is minimal.

### Subject & Storytelling
The image appears to be about a person, possibly in a casual or candid moment, given the informal attire and the relaxed posture. The subject is clearly anchored, but the frame could benefit from tighter composition to better support the narrative. The background, while not distracting, could be minimized to draw more attention to the subject.

### Technical Quality
The image appears sharp, with good detail visible in the subject's jacket and the background. The depth of field is shallow, focusing on the subject, which is appropriate for isolating the subject from the background. There are no visible noise or artifacts, indicating good image quality. The motion treatment seems static, as there is no indication of movement blur, which suggests the subject was either still or the shutter speed was fast enough to freeze motion.

### Verdict
The image has strong color and good exposure, but the composition could be tightened to better align with the rule of thirds and to enhance the subject's prominence. The background could be minimized to better support the narrative.

### Improved SDXL prompt

```
A candid moment of an elderly person wearing a vibrant red coat and hood, holding an object in hand, framed within a 35mm full-frame shot on a digital point-and-shoot from 2005-2010. The subject, positioned slightly off-center but adhering to the rule of thirds, is the focal point. The lighting is soft and diffused, with a warm 3200K color balance, emanating from overhead fluorescent light. The red jacket, sharp and saturated, contrasts with the subdued background. Compositional lines guide the viewer's eye towards the subject, while the background, consisting of framed artwork on the wall, serves as a subtle backdrop. The shot is crisp, with a shallow depth of field isolating the subject. The background, while framed, is minimally intrusive and harmonizes with the red jacket, complementing the neutral tones. The image exhibits natural sharpness and detail, with no visible noise or motion blur. The composition aligns well with the rule of thirds, creating a balanced and dynamic frame.
```

### AI tells observed in this round's sequel

- No clear AI tells observed.

### Blind A/B test (vs. original)

- Judge chose: **B**
- Mapping: `{'A': 'sequel', 'B': 'original'}`
- **Truth verdict: ORIGINAL**

---

## Round 2

**Input image:** `/Users/michaellinares/Documents/imgSequel/qwen_critique_loop/runs/20260505_075237_small/round_01/sequel.png`

**Sequel image:** `/Users/michaellinares/Documents/imgSequel/qwen_critique_loop/runs/20260505_075237_small/round_02/sequel.png`

### Critique

### Composition
The subject is placed in the bottom left third of the frame, which is a good use of the rule of thirds. The leading lines formed by the wall and the frames draw the viewer's eye towards the subject. The balance is slightly off, with the subject leaning slightly towards the bottom left corner, which could be improved for a more centered and balanced composition. Negative space is used effectively at the top of the frame, which helps to separate the subject from the background. The framing is simple and effective, focusing on the subject and the background artwork.

### Lighting
The lighting appears to be natural, possibly from a window out of frame, which provides a soft and even illumination. The shadows are soft and there is good detail in the subject's face and the objects she is holding. The color temperature is neutral, and the contrast is balanced, allowing for good separation of the subject from the background. The time of day implied by the lighting suggests it could be late afternoon or early evening.

### Exposure & Tonality
The exposure is well balanced, with no significant clipping in the highlights or shadows. The midtones are separated, allowing for good detail in both the subject and the background. The dynamic range is used effectively, with the subject and the background both well defined. The overall density of the image is appropriate, neither too dark nor too light.

### Color
The color palette is quite limited, with the red of the subject's coat being the most vibrant element. The background is mostly muted, with the artwork providing subtle tones. The saturation is consistent, and the color relationships are harmonious, with the red coat standing out against the more subdued background. There is no intentional dissonance, and the colors work together well to create a cohesive image.

### Subject & Storytelling
The image tells a story of an elderly person, possibly a collector or an artist, holding a small object that seems to be of significance. The subject is clearly anchored in the frame, and the background artwork adds context, suggesting a personal or professional space. The frame supports the narrative by focusing on the subject and the object she is holding, while the background provides a sense of setting.

### Technical Quality
The image appears sharp, with good detail in the subject's face and the object she is holding. The depth of field is shallow, which isolates the subject from the background. There are no noticeable noise or artifacts, indicating good technical quality. The motion treatment is non-existent, as the subject is stationary.

### Verdict
The image is well-composed and lit, with a harmonious color palette that supports the subject and the narrative. The single most fixable weakness is the slight imbalance in the composition, which could be improved by centering the subject more effectively.

### Improved SDXL prompt

```
An elderly person wearing a vibrant red coat and hood, holding a small object in hand, positioned slightly off-center but adhering to the rule of thirds, framed within a 35mm full-frame shot on a digital point-and-shoot from 2005-2010. The subject, slightly tilted and leaning towards the bottom left corner, is the focal point. The lighting is soft and diffused, with a warm 3200K color balance, emanating from overhead fluorescent light. Natural hand anatomy and visible skin pores on the hand, with five fingers clearly defined, add realism. The red jacket, sharp and saturated, contrasts with the subdued background. Compositional lines guide the viewer's eye towards the subject, while the background, consisting of framed artwork on the wall, serves as a subtle backdrop. The shot is crisp, with a shallow depth of field isolating the subject and a slight tilt to center the composition. The background, while framed, is minimally intrusive and harmonizes with the red jacket, complementing the neutral tones. The image exhibits natural sharpness and detail, with minimal motion blur on the hand and no visible noise or sensor noise. The composition aligns well with the rule of thirds, creating a balanced and dynamic frame.
```

### AI tells observed in this round's sequel

- Hands and fingers: The hands appear too smooth and lack natural creases and shadows, especially around the fingers.
- Eyes: The reflections in the eyes are overly symmetrical and lack the subtle imperfections seen in real eyes.
- Skin: The skin texture appears overly smooth and lacks the natural pores and imperfections found in real human skin.
- Hair: The hair strands appear too uniform and lack the natural variation and movement seen in real hair.
- Text and signs: The logo on the jacket appears too sharp and lacks the subtle imperfections and variations seen in real logos.
- Composition tells: The subject is hyper-centered, and the background elements appear too sharp and lack the subtle imperfections seen in real photography.

### Blind A/B test (vs. original)

- Judge chose: **B**
- Mapping: `{'A': 'sequel', 'B': 'original'}`
- **Truth verdict: ORIGINAL**

---

## Round 3

**Input image:** `/Users/michaellinares/Documents/imgSequel/qwen_critique_loop/runs/20260505_075237_small/round_02/sequel.png`

**Sequel image:** `/Users/michaellinares/Documents/imgSequel/qwen_critique_loop/runs/20260505_075237_small/round_03/sequel.png`

### Critique

### Composition
The subject is placed in the bottom left quadrant, which is not ideal for the rule of thirds. The framing is somewhat tight, focusing on the subject's hands and the camera, which might be a deliberate choice, but it leaves the viewer feeling slightly disconnected from the background. The balance is somewhat off, with the subject's red coat drawing the eye but not in harmony with the subdued tones of the background. Negative space is minimal, which could be intentional, but it might benefit from a bit more breathing room around the subject to enhance the overall composition.

### Lighting
The lighting appears to be artificial, possibly from a flash or a softbox, as there are no harsh shadows visible. The quality is soft, which is good for indoor photography, but the color temperature seems slightly warm, which could be balanced out with post-processing. The contrast is moderate, with good detail in both highlights and shadows, suggesting a good dynamic range.

### Exposure & Tonality
The exposure is balanced, with no obvious signs of overexposure or underexposure. The tonality is consistent, with the red coat standing out against the neutral background. The dynamic range usage is good, with the subject and the camera details visible without any noticeable clipping.

### Color
The color palette is dominated by the red of the coat, which is quite saturated and draws the eye. The background is muted, which works well to contrast with the red. The overall color consistency is good, but the red could be slightly less saturated to avoid overpowering the composition. The color relationships are clear, with the red coat and the black camera creating a strong contrast.

### Subject & Storytelling
The image seems to be about a person engaged in photography, possibly showcasing their work or technique. The subject is clearly anchored, with the camera being the focal point. The background frames the subject, but the tight framing might detract from the storytelling by limiting the viewer's understanding of the context. The frame supports the narrative but could be enhanced by a bit more context or space.

### Technical Quality
The image appears sharp, with good detail in the subject's hands and the camera. The depth of field is shallow, focusing on the camera, which is appropriate for the subject. There are no visible noise or artifacts, indicating good quality and a good camera choice for the task.

### Verdict
The image is strong in its use of color and contrast, with a clear subject and good technical quality. The most fixable weakness is the tight framing, which might benefit from a bit more context or space to enhance the storytelling.

### Improved SDXL prompt

```
An elderly person wearing a vibrant red coat and hood, holding a small object in hand, positioned in the lower-left third, adhering to the rule of thirds, framed within a 35mm full-frame shot on a digital point-and-shoot from 2005-2010. The subject is slightly tilted, with the red coat drawing the eye but not in harmony with the subdued tones of the background. The framing is tightened, focusing on the subject's hands and the camera, but the viewer feels connected to the background. The balance is slightly off, with the red coat and the camera details visible without any noticeable clipping. The image exhibits natural hand anatomy and visible skin pores on the hand, with five fingers clearly defined. The lighting is soft and diffused, with a warm 3200K color balance, emanating from overhead fluorescent light. Natural motion blur on the edges and sensor noise add realism. The red coat is sharp and saturated, contrasting with the muted background. The background, consisting of framed artwork on the wall, serves as a subtle backdrop, with slightly blurred elements. The image is crisp, with a shallow depth of field isolating the subject and a slight tilt to center the composition. The background is framed, but the viewer feels more connected to the context. The overall color palette is balanced, with the red coat dominating but not overpowering. The dynamic range usage is good, with the subject and the camera details visible without any noticeable clipping. The composition aligns well with the rule of thirds, creating a balanced and dynamic frame.
```

### AI tells observed in this round's sequel

- Hands and fingers: fingers appear too smooth and lack natural creases and shadows.
- Eyes: reflections in the eyes appear overly perfect and lack the natural imperfections seen in real eyes.
- Skin: the skin texture appears overly smooth and lacks the natural pores and imperfections.
- Hair: the hair appears too uniform and lacks the natural texture and movement seen in real hair.
- Text and signs: the logo on the red jacket appears too sharp and lacks the natural wear and tear seen in real logos.
- Backgrounds: the framed pictures on the wall appear too sharp and lack the natural wear and tear seen in real frames.
- Composition tells: the subject is hyper-centered, and the background elements appear too sharp and lack the natural bokeh seen in real photographs.
- Over-rendering: every surface appears uniformly sharp, and there is no atmospheric haze or natural detail loss.

### Blind A/B test (vs. original)

- Judge chose: **B**
- Mapping: `{'A': 'sequel', 'B': 'original'}`
- **Truth verdict: ORIGINAL**

---

## Round 4

**Input image:** `/Users/michaellinares/Documents/imgSequel/qwen_critique_loop/runs/20260505_075237_small/round_03/sequel.png`

**Sequel image:** `/Users/michaellinares/Documents/imgSequel/qwen_critique_loop/runs/20260505_075237_small/round_04/sequel.png`

### Critique

### Composition
The subject is positioned slightly off-center, adhering to the rule of thirds, which places the subject in a dynamic and visually engaging position within the frame. Leading lines are not immediately apparent, but the subject's posture and the direction of the camera subtly guide the viewer's eye toward the subject. The framing is tight, focusing on the individual, which creates a strong sense of intimacy. The balance is good, with the subject centrally placed, and there is sufficient negative space around her to avoid overcrowding. The subject placement is effective, as the viewer's attention is naturally drawn to the person holding the camera, making it the clear focal point. The geometry is simple and effective, with the lines of the jacket and the camera contributing to a harmonious composition.

### Lighting
The lighting appears to be natural, possibly from an indoor source with a warm tone, suggesting it might be taken during the golden hour or with artificial indoor lighting. The quality of light is soft, with minimal harsh shadows, indicating diffused light conditions. The color temperature is warm, which complements the red of the jacket and the earthy tones in the background. The contrast ratios are balanced, with the subject well-lit and the background slightly subdued, allowing the subject to stand out. The time of day implied is late afternoon or early evening, based on the warm lighting and the lack of strong, direct sunlight.

### Exposure & Tonality
The exposure seems well-balanced, with no significant overexposure or underexposure. The dynamic range is used effectively, capturing details in both the highlights and shadows. There is no visible clipping, and the midtones are well-separated, providing a good range of detail. The overall density is appropriate for the subject and the background, allowing for a clear distinction between the two. The image appears to be taken with a correct exposure setting, ensuring that the details of the jacket and the camera are visible and not washed out.

### Color
The color palette is cohesive, with the red of the jacket being the dominant color and complemented by the neutral tones of the background. The saturation is disciplined, with the red being the most saturated element, which helps draw attention to the subject. The color relationships are harmonious, with the warm tones of the jacket and background creating a pleasing visual flow. There is no intentional dissonance, and the colors work together well to create a balanced and aesthetically pleasing image.

### Subject & Storytelling
The image appears to be about a person who is engaged in photography, as indicated by the camera in her hand. The subject is clearly anchored, and the frame supports the narrative by focusing on the individual's interaction with the camera. The posture and the way she holds the camera suggest a sense of purpose and interest in the activity. The background, with its framed artwork, adds context, possibly indicating an artistic or creative environment. The image tells a story about someone who is passionate about photography and is likely proud of their work.

### Technical Quality
The image appears sharp, with the details in the jacket and the camera being clear and well-defined. The depth of field is shallow, with the subject in focus and the background slightly blurred, which helps to isolate the subject and draw attention to her. There are no visible motion artifacts, and the image appears to be taken with a steady hand or a tripod. The noise level is low, indicating that the image was taken with a high enough ISO setting or a fast enough shutter speed to minimize noise. There are no noticeable artifacts, and the overall technical quality is good.

### Verdict
The image excels in its composition, lighting, and storytelling, effectively capturing the subject's engagement with photography. The single most fixable weakness is the slight overexposure in the background, which could be mitigated by adjusting the exposure settings or using a neutral density filter.

### Improved SDXL prompt

```
An elderly person wearing a vibrant red coat and hood, holding a small object in hand, positioned in the lower-left third, adhering to the rule of thirds, framed within a 35mm full-frame shot on a digital point-and-shoot from 2005-2010. The subject is slightly tilted, with the red coat drawing the eye but not in harmony with the subdued tones of the background. The framing is tightened, focusing on the subject's hands and the camera, but the viewer feels connected to the background. The balance is slightly off, with the red coat and the camera details visible without any noticeable clipping. The image exhibits natural hand anatomy and visible skin pores on the hand, with five fingers clearly defined. The lighting is soft and diffused, with a warm 3200K color balance, emanating from overhead fluorescent light. Natural motion blur on the edges and sensor noise add realism. The red coat is sharp and saturated, contrasting with the muted background. The background, consisting of framed artwork on the wall, serves as a subtle backdrop, with slightly blurred elements. The image is crisp, with a shallow depth of field isolating the subject and a slight tilt to center the composition. The background is framed, but the viewer feels more connected to the context. The overall color palette is balanced, with the red coat dominating but not overpowering. The dynamic range usage is good, with the subject and the camera details visible without any noticeable clipping. The composition aligns well with the rule of thirds, creating a balanced and dynamic frame.
```

### AI tells observed in this round's sequel

- Hands and fingers: missing fingers, unnatural joint angles.
- Eyes: mismatched gaze, unnaturally symmetric reflections.
- Skin: waxy texture, missing pores, oversmoothed under-eye area.
- Hair: clumps that merge into background, hair-strand parallax that doesn't match head pose.
- Teeth: too uniform, blended into each other, wrong count.
- Text and signs: garbled letters, fake-looking logos.
- Jewellery, watches, buttons: warped clasps, asymmetric earrings, broken straps.
- Backgrounds: repeated patterns, out-of-context objects.
- Reflections and shadows: shadows that disagree with the implied light source, reflections that don't match the scene.
- Materials: cloth folds with no underlying physics, leather that looks painted, metal without real specular highlights.
- Composition tells: hyper-centered subject, unnatural bokeh boundaries, edge halos around the subject.
- Over-rendering: every surface uniformly sharp, no atmospheric haze, every detail "perfect".

### Blind A/B test (vs. original)

- Judge chose: **B**
- Mapping: `{'A': 'sequel', 'B': 'original'}`
- **Truth verdict: ORIGINAL**

---

## Round 5

**Input image:** `/Users/michaellinares/Documents/imgSequel/qwen_critique_loop/runs/20260505_075237_small/round_04/sequel.png`

**Sequel image:** `/Users/michaellinares/Documents/imgSequel/qwen_critique_loop/runs/20260505_075237_small/round_05/sequel.png`

### Critique

### Composition
The subject is placed in the bottom left third of the frame, which is a good use of the rule of thirds. The leading lines formed by the framed pictures on the wall guide the viewer's eye towards the subject. The balance appears slightly off-center, but the subject's position and the framed pictures create a dynamic composition. The negative space around the subject is minimal, which keeps the focus on the person and the camera. The overall geometry of the framed pictures and the subject's pose adds visual interest.

### Lighting
The lighting appears to be natural, possibly from a window out of frame, creating a soft quality with even illumination on the subject's face. The color temperature is neutral, and there are no harsh shadows or highlights, suggesting a diffused light source. The contrast ratios appear balanced, with the subject's red coat standing out against the muted background.

### Exposure & Tonality
The exposure seems well-balanced, with no noticeable clipping in the highlights or shadows. The midtones are separated, allowing the details in the subject's face and the camera to be visible. The overall density is appropriate for a portrait, with good separation between the subject and the background.

### Color
The color palette is limited, with the red coat being the most vibrant element. The background is subdued, with earth tones and muted colors. The red coat does not clash with the background but stands out, which could be seen as a cohesive choice. The saturation is consistent, with the red being the most saturated element, creating a harmonious yet distinct subject.

### Subject & Storytelling
The image appears to be about a photographer, possibly showcasing their work or a moment of creative expression. The subject's pose, holding the camera, and the framed pictures in the background suggest a connection to photography. The subject is clearly anchored in the frame, and the composition supports the narrative of a photographer's life or work.

### Technical Quality
The image appears sharp, with good detail in the subject's face and the camera. The depth of field is shallow, focusing on the subject while the background is slightly blurred, which is appropriate for a portrait. There are no visible artifacts, and the image appears clean and free from noise.

### Verdict
The image excels in composition, lighting, and technical quality, with a strong narrative about a photographer. The single most fixable weakness is the slight imbalance in the composition, which could be improved by shifting the subject slightly to the right or adding a bit more negative space around the subject for a more balanced feel.

### Improved SDXL prompt

```
An elderly person wearing a vibrant red coat and hood, holding a small object in hand, positioned in the upper-right third, adhering to the rule of thirds, framed within a 35mm full-frame shot on a digital point-and-shoot from 2005-2010. The subject is slightly tilted, with the red coat drawing the eye but not in harmony with the muted background. The framing is tightened, focusing on the subject's hands and the camera, but the viewer feels connected to the background. The balance is slightly off, with the red coat and the camera details visible without any noticeable clipping. The natural motion blur on the edges and sensor noise add realism. The red coat is sharp and saturated, contrasting with the muted background. The background, consisting of framed artwork on the wall, serves as a subtle backdrop, with slightly blurred elements and natural wear and tear. The image exhibits natural hand anatomy and visible skin pores on the hand, with five fingers clearly defined. The lighting is soft and diffused, with a warm 3200K color balance, emanating from overhead fluorescent light. Natural motion blur on the edges and sensor noise add realism. The logo on the red jacket appears sharp and lacks the natural wear and tear seen in real logos. The framed pictures on the wall appear sharp and lack the natural wear and tear seen in real frames. The overall color palette is balanced, with the red coat dominating but not overpowering. The dynamic range usage is good, with the subject and the camera details visible without any noticeable clipping. The composition aligns well with the rule of thirds, creating a balanced and dynamic frame.
```

### AI tells observed in this round's sequel

- No clear AI tells observed.

### Blind A/B test (vs. original)

- Judge chose: **B**
- Mapping: `{'A': 'original', 'B': 'sequel'}`
- **Truth verdict: SEQUEL**

---

## Cumulative AI-tells log

--- Round 1 sequel — observed tells ---
- No clear AI tells observed.
--- Round 2 sequel — observed tells ---
- Hands and fingers: The hands appear too smooth and lack natural creases and shadows, especially around the fingers.
- Eyes: The reflections in the eyes are overly symmetrical and lack the subtle imperfections seen in real eyes.
- Skin: The skin texture appears overly smooth and lacks the natural pores and imperfections found in real human skin.
- Hair: The hair strands appear too uniform and lack the natural variation and movement seen in real hair.
- Text and signs: The logo on the jacket appears too sharp and lacks the subtle imperfections and variations seen in real logos.
- Composition tells: The subject is hyper-centered, and the background elements appear too sharp and lack the subtle imperfections seen in real photography.
--- Round 3 sequel — observed tells ---
- Hands and fingers: fingers appear too smooth and lack natural creases and shadows.
- Eyes: reflections in the eyes appear overly perfect and lack the natural imperfections seen in real eyes.
- Skin: the skin texture appears overly smooth and lacks the natural pores and imperfections.
- Hair: the hair appears too uniform and lacks the natural texture and movement seen in real hair.
- Text and signs: the logo on the red jacket appears too sharp and lacks the natural wear and tear seen in real logos.
- Backgrounds: the framed pictures on the wall appear too sharp and lack the natural wear and tear seen in real frames.
- Composition tells: the subject is hyper-centered, and the background elements appear too sharp and lack the natural bokeh seen in real photographs.
- Over-rendering: every surface appears uniformly sharp, and there is no atmospheric haze or natural detail loss.
--- Round 4 sequel — observed tells ---
- Hands and fingers: missing fingers, unnatural joint angles.
- Eyes: mismatched gaze, unnaturally symmetric reflections.
- Skin: waxy texture, missing pores, oversmoothed under-eye area.
- Hair: clumps that merge into background, hair-strand parallax that doesn't match head pose.
- Teeth: too uniform, blended into each other, wrong count.
- Text and signs: garbled letters, fake-looking logos.
- Jewellery, watches, buttons: warped clasps, asymmetric earrings, broken straps.
- Backgrounds: repeated patterns, out-of-context objects.
- Reflections and shadows: shadows that disagree with the implied light source, reflections that don't match the scene.
- Materials: cloth folds with no underlying physics, leather that looks painted, metal without real specular highlights.
- Composition tells: hyper-centered subject, unnatural bokeh boundaries, edge halos around the subject.
- Over-rendering: every surface uniformly sharp, no atmospheric haze, every detail "perfect".
--- Round 5 sequel — observed tells ---
- No clear AI tells observed.
