#!/usr/bin/python
import json, os, shutil, subprocess, platform

sed = 'sed'
if platform.system() == 'Darwin': sed = 'gsed'
build_dir = "build"
tmp_dir = "tmp"
github_base = "https://github.com/apigovau/"
main_repo = github_base + "api-gov-au"
deps = [
        github_base + "/repository",
        github_base + "/key-manager",
        github_base + "/service-editor"
]
mods = [
    ("s/APIController/APIControllerRepository/g", build_dir + "/src/main/kotlin/au/gov/api/repository/APIController.kt"),
    ("s/APIController/APIControllerRepository/g", build_dir + "/src/main/kotlin/au/gov/api/repository/GitHub.kt"),
    ("s/APIController/APIControllerRegistration/g", build_dir + "/src/main/kotlin/au/gov/api/registration/APIController.kt"),
    ("s/com.github.apigovau:config:v1.0/com.github.apigovau:config:v2/g", build_dir + "/build.gradle"),
    ("s_Mapping(\\\"_Mapping(\\\"/repository_g", build_dir + "/src/main/kotlin/au/gov/api/repository/APIController.kt"),
    ("s_Mapping(\\\"_Mapping(\\\"/repository_g", build_dir + "/src/main/kotlin/au/gov/api/repository/definitions/DefinitionsController.kt"),
    ("s_Mapping(\\\"_Mapping(\\\"/keys/producer_g", build_dir + "/src/main/kotlin/au/gov/api/registration/APIController.kt"),
    ("\\$aspring.datasource.url=jdbc:postgresql://localhost:5432/postgres?user=postgres&password=mysecretpassword",build_dir + "/src/main/resources/application-default.properties")
#('$!N; s/@Autowired\s*\\n.*DataSource/private var dataSource: DataSource = dataSource()!!/g', build_dir + "/src/main/kotlin/au/gov/api/registration/RegistrationManager.kt")
]



def setup_folder(folder):
    if os.path.exists(folder): shutil.rmtree(folder)
    os.mkdir(folder)



def folder_from_repo(repo): return repo.split("/")[-1]



def git_checkout(repo):
    repo_folder = folder_from_repo(repo)
    print " - checking out " + repo_folder 
    output = subprocess.check_output(['git', 'clone', '-q', repo, 'tmp/' + repo_folder ])



def is_cache_valid():
    for repo in [main_repo] + deps:
        if not os.path.exists(tmp_dir + '/' + folder_from_repo(repo)): return False
    print " - reusing cache"
    return True



def get_gradle_dependencies(folder):
    build_gradle = folder + "/build.gradle"
    if not os.path.exists(build_gradle): return 0,0,""
    print "   - getting gradle dependencies for " + folder.replace(tmp_dir + "/","") 
    f = open(build_gradle, "r")
    build_file = f.readlines()
    f.close()
    dep_start = build_file.index("dependencies {\n") + 1
    dep_end = build_file[dep_start:].index("}\n") + dep_start
    return dep_start, dep_end, "// " + folder.replace(tmp_dir + "/","") + "\n" + "".join(build_file[dep_start:dep_end])



def get_all_dependencies():
    all_deps = ""
    for proj in map(lambda x: tmp_dir + "/" + folder_from_repo(x), [main_repo] + deps):
        start, end, the_deps = get_gradle_dependencies(proj)
        all_deps = all_deps + "\n" + the_deps
    return all_deps



def generate_main_build_gradle():
    print " - generating merged build.gradle" 
    all_deps = get_all_dependencies()
    build_gradle = tmp_dir + "/" + folder_from_repo(main_repo) + "/build.gradle"
    f = open(build_gradle, "r")
    build_file = f.readlines()
    dep_start = build_file.index("dependencies {\n") + 1
    dep_end = build_file[dep_start:].index("}\n") + dep_start

    new_build_gradle = "".join(build_file[0:dep_start])
    new_build_gradle += all_deps + "\n"
    new_build_gradle += "".join(build_file[dep_end:])
    f.close()
    return new_build_gradle



def copy_repos_to_build():
    print " - copying projects to bulid dir"
    for proj in map(lambda x: tmp_dir + "/" + folder_from_repo(x), deps + [main_repo]):
        print "    - " + proj.replace(tmp_dir + "/","")
        os.system("cp -rf " + proj + "/* " + build_dir)



def write_new_build_gradlew():
    f = open(build_dir + "/build.gradle", "w")
    f.write(generate_main_build_gradle())
    f.write("\n")
    f.close()



def execute_sed(regex, theFile):
    output = subprocess.call([sed + " -i -e \"" + regex + "\" " +  theFile ],shell=True)


def make_modifications():
    print " - modifying code"
    for mod in mods:
        execute_sed(mod[0], mod[1])

def create_env():
    print " - creating environment variables"
    f = open(build_dir + "/.env", "w")
    f.write("config_environment=api.gov.au\n")
    f.write("apigov_config_BaseRepoURI=http://localhost:5000/repository/\n")
    f.write("apigov_config_AuthURI=http://localhost:5000/keys/producer/\n")
    f.write("BootstrapCredentials=abcd:1234\n")
    f.close()



print "Compiliing monolith deployment for api.gov.au"
setup_folder(build_dir)
if not is_cache_valid():
    setup_folder(tmp_dir)
    map(git_checkout, [main_repo] + deps)
copy_repos_to_build()
write_new_build_gradlew()
make_modifications()
create_env()
print "done."

