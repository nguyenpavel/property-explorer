Flat D.601, Mocca Rezidence (building D, 6th floor, 3+kk): 3D model for rendering
==================================================================================

FILES
  D601_Mocca_flat.fbx    The model. Use this for 3ds Max (Corona, V-Ray, Arnold), and also
                         for Lumion, Twinmotion, D5 Render, Enscape and Unreal.
  D601_Mocca_flat.fbm\   Its textures. They are also embedded in the FBX.
  obj\                   The same model as OBJ + MTL, for programs that don't read FBX.


OPENING IT IN 3DS MAX
  File > Import > Import..., then choose D601_Mocca_flat.fbx. In the FBX Import dialog:
  - Units: leave "Automatic" on. The file is in centimetres, and Max converts it to your
    system units.
  - Axis Conversion: Up Axis "Z-up". The file already uses Max's own axis system.
  - Embed Media: leave "Extract Media" on.

  To check the size, measure Floor 02 (living room + kitchen). It is 7.23 x 3.72 m (26.9 m²).
  The ceiling is at 2.70 m. The whole flat is 10.50 x 12.08 m. The model is at true size.
  +Y is the top of the developer's sales sheet, which is not necessarily north.
  Every object comes in with rotation 0 and scale 100%.


WHAT'S IN IT (71 objects, grouped under 7 parent dummies)
  Structure              Walls: one solid, with no buried faces. Floor slab: concrete under
                         the flat. Ceiling: a slab at 2.70 m; hide it for views from above.
  Floors                 One object per room: Floor 01 Hall ... Floor 08 Loggia. Each is a
                         20 mm finish on the slab. Floor thresholds fill the doorways.
  Doors                  A frame and a leaf for each of the 9 doors. The leaves stand open,
                         as the plan draws them, and pivot on their hinges. To shut a leaf,
                         rotate it about its local Z by the angle in
                         Object Properties > User Defined: close_angle_deg = 90 or -90.
  Windows and loggia     The windows, the loggia glazing posts and the glass railings.
  Kitchen and bathrooms  Kitchen units, sink, hob, bathtub, two WCs, basins, towel rail and
                         washing machine.
  Furniture              Placed where the plan draws it. Each piece pivots at its bottom
                         centre.
  Reference              The developer's sales plan as a textured plane, at true scale,
                         26 cm under the slab. Hide or delete it for renders.

  The FBX has no lights and no cameras. Add your own sun and sky (Corona or V-Ray) and your
  own cameras. The window and loggia glass is real geometry, so daylight can come in.


MATERIALS AND UVS
  The materials are simple placeholders, named by finish: Plaster, Ceiling, Concrete,
  Oak planks, Bath floor tiles, Loggia tiles, Oak, White lacquer, Anthracite, Glass, Chrome,
  Steel, Ceramic, Black glass, Sofa fabric, Bedding, Cushion, Wardrobe. They import as
  plain Max materials carrying their colours. Replace them with your Corona or V-Ray
  materials.
  Every face has box-projected UVs in real-world metres: a map with tiling 1 covers
  1 x 1 m. On the floors, the UVs are scaled to their own plank and tile maps instead.
  If you prefer, put a UVW Map (Box) modifier with real-world map size on top.


ASSUMPTIONS
  The plan comes from the developer's sales sheet. It is scaled from its area table, and
  every room matches the table to 0.1 m².
  The plan gives no heights, so these are assumed: ceiling 2.70 m, interior doors 2.10 m,
  front door 2.20 m, windows from 0.85 to 2.30 m, kitchen worktop 0.90 m, loggia railing
  1.10 m.
  The furniture and finishes are illustrative.


OBJ VERSION
  Y-up and in metres, as OBJ files usually are.
  - 3ds Max's OBJ importer: keep "Flip ZY-axis" on and import as metres.
  - Other programs: import as metres.
  OBJ has no pivots or hierarchy, so the door leaves pivot at the world origin.
