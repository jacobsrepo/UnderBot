cmake_minimum_required(VERSION 3.16)
project(underbot_description)

find_package(ament_cmake REQUIRED)

# This package contains description assets only. A simulator or hardware
# interface supplies joint feedback and actuation separately.
install(DIRECTORY urdf meshes launch rviz config docs
  DESTINATION share/${PROJECT_NAME}
)
install(FILES README.md DESTINATION share/${PROJECT_NAME})
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/viewer.html")
  install(FILES viewer.html DESTINATION share/${PROJECT_NAME})
endif()

# CAD and generation tools are delivered as source resources when present.
foreach(resource_dir IN ITEMS cad scripts validation)
  if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${resource_dir}")
    install(DIRECTORY ${resource_dir} DESTINATION share/${PROJECT_NAME})
  endif()
endforeach()

ament_package()
