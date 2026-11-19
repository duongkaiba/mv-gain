# Data audit

Objects: 39790  |  overall pass: **False**

## Blocking checks

| Check | Violations |
| --- | --- |
| wrong_view_count | 0 |
| duplicate_view_ids | 0 |
| label_vs_view_or_mismatch | 4 |
| objects_with_missing_image | 0 |

## Non-blocking

| Check | Count |
| --- | --- |
| objects_with_missing_mask | 0 |
| mask_size_mismatch | 94 |
| duplicate_content_hash | 111 |

## Annotation status

| Status | Count |
| --- | --- |
| empty_mask_on_anomaly | 4 |
| mask_size_mismatch | 94 |
| ok | 39692 |

## Per category

| Category | objects | normal | anomalous | mean k | P(k<=2) | median defect area | thin strata |
| --- | --- | --- | --- | --- | --- | --- | --- |
| circular_aviation_connector | 248 | 50 | 198 | 4.379 | 0.1616 | 0.005393 | 1,3,4 |
| lego_turbine | 250 | 50 | 200 | 4.36 | 0.16 | 0.043671 | 1,3,4 |
| limit_switch | 250 | 50 | 200 | 4.445 | 0.11 | 0.021825 | 2 |
| green_ring_filter | 250 | 50 | 200 | 4.37 | 0.085 | 0.008788 | 1 |
| vertical_adjustable_resistor | 250 | 50 | 200 | 4.465 | 0.085 | 0.011241 | - |
| rectangular_connector_accessories | 250 | 50 | 200 | 3.965 | 0.065 | 0.00572 | 1 |
| fork_crimp_terminal | 246 | 50 | 196 | 4.617 | 0.0612 | 0.01127 | 1,2,3 |
| spring_antenna | 250 | 50 | 200 | 4.785 | 0.04 | 0.025904 | 1,2,3 |
| laser_diode | 243 | 50 | 193 | 4.777 | 0.0311 | 0.004532 | 1,2,3 |
| pulse_transformer | 245 | 50 | 195 | 4.938 | 0.0205 | 0.021988 | 2 |
| thumbtack | 249 | 50 | 199 | 4.709 | 0.0201 | 0.007302 | 1,2,3 |
| mouse_socket | 246 | 50 | 196 | 4.806 | 0.0153 | 0.007093 | 1,2,3 |
| boost_converter_module | 248 | 50 | 198 | 4.707 | 0.0152 | 0.028895 | 1,2 |
| insect_metal_parts | 248 | 50 | 198 | 4.894 | 0.0152 | 0.017079 | 1,2,3,4 |
| vibration_motor | 250 | 50 | 200 | 4.78 | 0.015 | 0.007721 | 2,3 |
| little_cow_model | 249 | 50 | 199 | 4.809 | 0.0101 | 0.008971 | 1 |
| retaining_ring | 248 | 50 | 198 | 4.641 | 0.0101 | 0.070495 | 2 |
| audio_jack_socket | 250 | 50 | 200 | 4.655 | 0.01 | 0.004634 | 2,3 |
| bend_connector | 250 | 50 | 200 | 4.905 | 0.01 | 0.014118 | 2 |
| crimp_st_cable_mount_box | 250 | 50 | 200 | 4.915 | 0.01 | 0.01246 | 1,4 |
| motor_gear_reducer | 250 | 50 | 200 | 4.96 | 0.01 | 0.010571 | 2,4 |
| red_terminal | 250 | 50 | 200 | 4.875 | 0.01 | 0.015371 | 1,2,3 |
| lego_technical_gear | 243 | 50 | 193 | 4.902 | 0.0052 | 0.013343 | 2,3 |
| accurate_detection_switch | 247 | 49 | 198 | 4.955 | 0.0051 | 0.037015 | 2,4 |
| battery_holder_connector | 247 | 50 | 197 | 4.98 | 0.0051 | 0.019846 | 1 |
| charging_port | 248 | 50 | 198 | 4.949 | 0.0051 | 0.02053 | 2,3,4 |
| dc_jack | 248 | 50 | 198 | 4.763 | 0.0051 | 0.034669 | 2,3 |
| duckbill_circuit_breaker | 247 | 50 | 197 | 4.914 | 0.0051 | 0.009167 | 2,3 |
| monitor_socket | 247 | 50 | 197 | 4.985 | 0.0051 | 0.015147 | 2 |
| aircraft_model_head | 250 | 50 | 200 | 4.97 | 0.005 | 0.011785 | 2,3,4 |
| button_battery_holder | 249 | 50 | 199 | 4.985 | 0.005 | 0.013609 | 2 |
| common_mode_choke | 250 | 50 | 200 | 4.69 | 0.005 | 0.028865 | 2 |
| effect_transistor | 250 | 50 | 200 | 4.61 | 0.005 | 0.015902 | 2,3 |
| jam_jar_model | 249 | 50 | 199 | 4.688 | 0.005 | 0.017585 | 2,3 |
| lattice_block_plug | 249 | 50 | 199 | 4.724 | 0.005 | 0.006209 | 2 |
| meteor_hammer_arrowhead | 250 | 50 | 200 | 4.765 | 0.005 | 0.015497 | 1,3 |
| motor_plug | 250 | 50 | 200 | 4.975 | 0.005 | 0.049155 | 1,4 |
| pot_core | 250 | 50 | 200 | 4.98 | 0.005 | 0.049033 | 2,4 |
| power_inductor | 249 | 50 | 199 | 4.91 | 0.005 | 0.017001 | 2,3,4 |
| power_jack | 250 | 50 | 200 | 4.985 | 0.005 | 0.00346 | 2 |
| self_lock_switch | 250 | 50 | 200 | 4.985 | 0.005 | 0.004597 | 2 |
| single_pole_potentiometer | 250 | 50 | 200 | 4.92 | 0.005 | 0.007057 | 2,3 |
| toy_tire | 247 | 47 | 200 | 4.87 | 0.005 | 0.02531 | 2,3 |
| vehicle_harness_conductor | 250 | 50 | 200 | 4.86 | 0.005 | 0.005985 | 1 |
| 2pin_block_plug | 248 | 48 | 200 | 4.985 | 0.0 | 0.107748 | 3,4 |
| 3_adapter | 249 | 50 | 199 | 4.99 | 0.0 | 0.01067 | 4 |
| 3pin_aviation_connector | 247 | 50 | 197 | 4.959 | 0.0 | 0.016566 | 4 |
| 4_wire_stepping_motor | 250 | 50 | 200 | 5.0 | 0.0 | 0.002341 | - |
| DVD_switch | 250 | 50 | 200 | 5.0 | 0.0 | 0.02403 | - |
| D_sub_connector | 246 | 50 | 196 | 4.918 | 0.0 | 0.017843 | - |
| LED_indicator | 248 | 50 | 198 | 5.0 | 0.0 | 0.007123 | - |
| PLCC_socket | 250 | 50 | 200 | 5.0 | 0.0 | 0.007236 | - |
| VR_joystick | 250 | 50 | 200 | 4.775 | 0.0 | 0.011062 | - |
| access_card | 247 | 50 | 197 | 5.0 | 0.0 | 0.005059 | - |
| angled_toggle_switch | 250 | 50 | 200 | 4.985 | 0.0 | 0.026814 | 3,4 |
| bag_buckle | 247 | 49 | 198 | 5.0 | 0.0 | 0.007954 | - |
| ball_pin | 250 | 50 | 200 | 4.995 | 0.0 | 0.011263 | 4 |
| balun_transformer | 248 | 50 | 198 | 4.753 | 0.0 | 0.018739 | 3 |
| battery | 250 | 50 | 200 | 4.98 | 0.0 | 0.01043 | 3 |
| battery_socket_connector | 250 | 50 | 200 | 4.81 | 0.0 | 0.024305 | - |
| blade_switch | 250 | 50 | 200 | 5.0 | 0.0 | 0.012701 | - |
| blue_light_switch | 249 | 50 | 199 | 4.854 | 0.0 | 0.008405 | - |
| bluetooth_module | 249 | 50 | 199 | 5.0 | 0.0 | 0.045926 | - |
| bread_model | 250 | 50 | 200 | 4.865 | 0.0 | 0.005232 | 3 |
| brooch_clasp_accessory | 250 | 50 | 200 | 4.935 | 0.0 | 0.054591 | - |
| button_motor | 246 | 50 | 196 | 5.0 | 0.0 | 0.009815 | - |
| button_switch | 250 | 50 | 200 | 5.0 | 0.0 | 0.005779 | - |
| car_door_lock_switch | 250 | 50 | 200 | 5.0 | 0.0 | 0.006401 | - |
| ceramic_fuse | 250 | 50 | 200 | 5.0 | 0.0 | 0.013378 | - |
| ceramic_wave_filter | 249 | 50 | 199 | 5.0 | 0.0 | 0.011966 | - |
| chip_inductor | 249 | 50 | 199 | 4.995 | 0.0 | 0.049406 | 4 |
| circuit_breaker | 249 | 50 | 199 | 4.99 | 0.0 | 0.015422 | 3 |
| common_mode_filter | 250 | 50 | 200 | 4.97 | 0.0 | 0.038828 | 4 |
| connector | 245 | 50 | 195 | 4.974 | 0.0 | 0.085954 | 4 |
| connector_housing_female | 250 | 50 | 200 | 4.995 | 0.0 | 0.033362 | 4 |
| console_switch | 248 | 50 | 198 | 5.0 | 0.0 | 0.009936 | - |
| dc_power_connector | 250 | 50 | 200 | 5.0 | 0.0 | 0.006013 | - |
| detection_switch | 250 | 50 | 200 | 4.695 | 0.0 | 0.00666 | 3 |
| earphone_audio_unit | 250 | 50 | 200 | 4.9 | 0.0 | 0.026371 | - |
| electronic_watch_movement | 248 | 50 | 198 | 5.0 | 0.0 | 0.008064 | - |
| ethernet_connector | 224 | 50 | 174 | 4.908 | 0.0 | 0.008262 | 3 |
| ferrite_bead | 250 | 50 | 200 | 4.955 | 0.0 | 0.0027 | 4 |
| ffc_connector_plug | 250 | 50 | 200 | 4.745 | 0.0 | 0.00625 | - |
| flow_control_valve | 247 | 49 | 198 | 4.874 | 0.0 | 0.005026 | 3 |
| flower_copper_shape | 249 | 50 | 199 | 5.0 | 0.0 | 0.024722 | - |
| flower_velvet_fabric | 250 | 50 | 200 | 5.0 | 0.0 | 0.04415 | - |
| fuse_cover | 247 | 47 | 200 | 4.75 | 0.0 | 0.00508 | - |
| fuse_holder | 249 | 50 | 199 | 5.0 | 0.0 | 0.010899 | - |
| gear | 250 | 50 | 200 | 4.995 | 0.0 | 0.038275 | 4 |
| gear_motor | 249 | 50 | 199 | 5.0 | 0.0 | 0.003876 | - |
| hairdryer_switch | 250 | 50 | 200 | 5.0 | 0.0 | 0.00404 | - |
| hall_effect_sensor | 248 | 50 | 198 | 5.0 | 0.0 | 0.026233 | - |
| headphone_jack_female | 249 | 50 | 199 | 4.99 | 0.0 | 0.023038 | 4 |
| headphone_jack_socket | 250 | 50 | 200 | 4.975 | 0.0 | 0.020022 | 4 |
| hex_plug | 250 | 50 | 200 | 5.0 | 0.0 | 0.012636 | - |
| humidity_sensor | 249 | 50 | 199 | 4.955 | 0.0 | 0.00941 | 4 |
| ingot_buckle | 249 | 50 | 199 | 5.0 | 0.0 | 0.008259 | - |
| inverter_connector | 250 | 50 | 200 | 5.0 | 0.0 | 0.009513 | - |
| joystick_switch | 248 | 50 | 198 | 5.0 | 0.0 | 0.005854 | - |
| kfc_push_key_switch | 249 | 50 | 199 | 4.98 | 0.0 | 0.004348 | 4 |
| knob_cap | 249 | 50 | 199 | 4.799 | 0.0 | 0.020878 | - |
| lego_pin_connector_plate | 248 | 50 | 198 | 4.985 | 0.0 | 0.018074 | 4 |
| lego_propeller | 250 | 50 | 200 | 4.965 | 0.0 | 0.00735 | 3,4 |
| lego_reel | 245 | 50 | 195 | 5.0 | 0.0 | 0.012733 | - |
| lighting_connector | 248 | 50 | 198 | 4.631 | 0.0 | 0.022838 | - |
| lilypad_led | 248 | 50 | 198 | 5.0 | 0.0 | 0.007638 | - |
| lithium_battery_plug | 249 | 50 | 199 | 4.899 | 0.0 | 0.008471 | 3 |
| littel_fuse | 250 | 50 | 200 | 4.995 | 0.0 | 0.029048 | 4 |
| lock | 250 | 50 | 200 | 4.905 | 0.0 | 0.030409 | 3 |
| long_zipper | 249 | 50 | 199 | 4.94 | 0.0 | 0.006802 | 3,4 |
| miniature_laser_module | 242 | 50 | 192 | 4.984 | 0.0 | 0.009586 | 4 |
| miniature_lifting_motor | 250 | 50 | 200 | 4.985 | 0.0 | 0.010619 | 4 |
| miniature_motor | 249 | 49 | 200 | 4.985 | 0.0 | 0.009838 | 3,4 |
| miniature_stepper_motor | 250 | 50 | 200 | 5.0 | 0.0 | 0.032024 | - |
| mobile_charging_connector | 250 | 50 | 200 | 5.0 | 0.0 | 0.021955 | - |
| model_steering_module | 250 | 50 | 200 | 4.775 | 0.0 | 0.004422 | 3 |
| motor_bracket | 249 | 50 | 199 | 4.99 | 0.0 | 0.020511 | 4 |
| multi_function_switch | 250 | 50 | 200 | 5.0 | 0.0 | 0.015675 | - |
| nylon_ball_head | 250 | 50 | 200 | 5.0 | 0.0 | 0.017063 | - |
| optical_fiber_outlet | 248 | 48 | 200 | 4.99 | 0.0 | 0.013087 | 4 |
| pencil_sharpener | 249 | 50 | 199 | 4.945 | 0.0 | 0.005116 | 3,4 |
| pinboard_connector | 250 | 50 | 200 | 5.0 | 0.0 | 0.014063 | - |
| pitch_connector | 248 | 50 | 198 | 4.838 | 0.0 | 0.013367 | - |
| pneumatic_elbow | 250 | 50 | 200 | 4.985 | 0.0 | 0.021475 | 4 |
| potentiometer | 248 | 50 | 198 | 4.702 | 0.0 | 0.006536 | - |
| power_bank_module | 245 | 50 | 195 | 4.928 | 0.0 | 0.022918 | - |
| power_strip_socket | 250 | 50 | 200 | 4.29 | 0.0 | 0.007351 | - |
| purple_clay_pot | 242 | 50 | 192 | 4.943 | 0.0 | 0.015811 | 4 |
| push_button_switch | 250 | 50 | 200 | 4.935 | 0.0 | 0.002962 | - |
| push_in_terminal | 248 | 48 | 200 | 4.995 | 0.0 | 0.00695 | 4 |
| recorder_switch | 250 | 50 | 200 | 4.99 | 0.0 | 0.003027 | 3 |
| rheostat | 249 | 50 | 199 | 4.995 | 0.0 | 0.005699 | 4 |
| rotary_position_sensor | 250 | 50 | 200 | 4.855 | 0.0 | 0.011005 | - |
| round_twist_switch | 250 | 50 | 200 | 4.93 | 0.0 | 0.005224 | 3 |
| shelf_support_module | 250 | 50 | 200 | 4.975 | 0.0 | 0.040474 | 3,4 |
| side_press_switch | 247 | 50 | 197 | 5.0 | 0.0 | 0.024128 | - |
| side_release_buckle | 250 | 50 | 200 | 4.99 | 0.0 | 0.003905 | 3 |
| silicon_cell_sensor | 250 | 50 | 200 | 5.0 | 0.0 | 0.007019 | - |
| sim_card_reader | 246 | 50 | 196 | 4.985 | 0.0 | 0.012115 | 3,4 |
| single_switch | 250 | 50 | 200 | 4.995 | 0.0 | 0.003418 | 4 |
| slide_switch | 249 | 50 | 199 | 4.98 | 0.0 | 0.01621 | 4 |
| slipper_model | 250 | 50 | 200 | 5.0 | 0.0 | 0.011318 | - |
| small_leaf | 250 | 50 | 200 | 4.825 | 0.0 | 0.003879 | 3 |
| smd_receiver_module | 249 | 50 | 199 | 4.553 | 0.0 | 0.018796 | 3 |
| solderless_adapter | 250 | 50 | 200 | 5.0 | 0.0 | 0.013814 | - |
| spherical_airstone | 246 | 48 | 198 | 4.909 | 0.0 | 0.008532 | 3 |
| square_terminal | 249 | 49 | 200 | 4.995 | 0.0 | 0.029724 | 4 |
| steering_T_head | 250 | 50 | 200 | 4.995 | 0.0 | 0.024684 | 4 |
| steering_wheel | 250 | 50 | 200 | 5.0 | 0.0 | 0.013831 | - |
| suction_cup | 250 | 50 | 200 | 4.82 | 0.0 | 0.030133 | 3 |
| telephone_spring_switch | 250 | 50 | 200 | 5.0 | 0.0 | 0.007892 | - |
| tension_snap_release_clip | 248 | 50 | 198 | 4.98 | 0.0 | 0.024059 | 4 |
| thyristor | 250 | 50 | 200 | 4.995 | 0.0 | 0.008909 | 4 |
| traceless_hair_clip | 250 | 50 | 200 | 4.975 | 0.0 | 0.01187 | 4 |
| travel_switch | 250 | 50 | 200 | 5.0 | 0.0 | 0.013174 | - |
| travel_switch_green | 249 | 50 | 199 | 5.0 | 0.0 | 0.013315 | - |
| tubular_key_switch | 248 | 50 | 198 | 5.0 | 0.0 | 0.012929 | - |
| vacuum_switch | 250 | 50 | 200 | 5.0 | 0.0 | 0.001991 | - |
| volume_potentiometer | 249 | 50 | 199 | 4.709 | 0.0 | 0.019835 | 3 |
| wireless_receiver_module | 248 | 50 | 198 | 5.0 | 0.0 | 0.022697 | - |
