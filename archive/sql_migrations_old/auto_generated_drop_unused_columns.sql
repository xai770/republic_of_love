-- Auto-generated migration: Drop unused columns
-- Generated: 2025-11-20 08:07:20
-- 
-- This migration drops columns that are:
-- 1. Not referenced in any Python or SQL code
-- 2. Either completely empty, contain only one constant value, or have < 5 rows
--
-- ⚠️ REVIEW THIS BEFORE EXECUTING ⚠️

BEGIN;

-- Drop conversations.app_scope (DELETE_CONSTANT: 599 rows, 1 distinct)
-- Sample values: talent
ALTER TABLE "conversations" DROP COLUMN IF EXISTS "app_scope";

-- Drop human_tasks.timeout_at (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "human_tasks" DROP COLUMN IF EXISTS "timeout_at";

-- Drop posting_skills.posting_skill_id (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "posting_skills" DROP COLUMN IF EXISTS "posting_skill_id";

-- Drop posting_state_snapshots.snapshot_id (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "posting_state_snapshots" DROP COLUMN IF EXISTS "snapshot_id";

-- Drop posting_state_snapshots.aggregate_version (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "posting_state_snapshots" DROP COLUMN IF EXISTS "aggregate_version";

-- Drop posting_state_snapshots.snapshot_data (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "posting_state_snapshots" DROP COLUMN IF EXISTS "snapshot_data";

-- Drop profile_certifications.credential_id (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_certifications" DROP COLUMN IF EXISTS "credential_id";

-- Drop profile_certifications.credential_url (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_certifications" DROP COLUMN IF EXISTS "credential_url";

-- Drop profile_certifications.does_not_expire (DELETE_CONSTANT: 12 rows, 1 distinct)
-- Sample values: f
ALTER TABLE "profile_certifications" DROP COLUMN IF EXISTS "does_not_expire";

-- Drop profile_education.education_id (DELETE_SPARSE: 3 rows, 3 distinct)
-- Sample values: 1, 2, 3
ALTER TABLE "profile_education" DROP COLUMN IF EXISTS "education_id";

-- Drop profile_education.institution_location (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_education" DROP COLUMN IF EXISTS "institution_location";

-- Drop profile_education.degree_name (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_education" DROP COLUMN IF EXISTS "degree_name";

-- Drop profile_education.gpa (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_education" DROP COLUMN IF EXISTS "gpa";

-- Drop profile_education.thesis_title (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_education" DROP COLUMN IF EXISTS "thesis_title";

-- Drop profile_education.relevant_coursework (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_education" DROP COLUMN IF EXISTS "relevant_coursework";

-- Drop profile_job_matches.match_id (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_job_matches" DROP COLUMN IF EXISTS "match_id";

-- Drop profile_job_matches.overall_match_score (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_job_matches" DROP COLUMN IF EXISTS "overall_match_score";

-- Drop profile_job_matches.skill_match_score (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_job_matches" DROP COLUMN IF EXISTS "skill_match_score";

-- Drop profile_job_matches.experience_match_score (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_job_matches" DROP COLUMN IF EXISTS "experience_match_score";

-- Drop profile_job_matches.location_match_score (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_job_matches" DROP COLUMN IF EXISTS "location_match_score";

-- Drop profile_job_matches.extra_skills (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_job_matches" DROP COLUMN IF EXISTS "extra_skills";

-- Drop profile_job_matches.match_quality (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_job_matches" DROP COLUMN IF EXISTS "match_quality";

-- Drop profile_job_matches.match_explanation (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_job_matches" DROP COLUMN IF EXISTS "match_explanation";

-- Drop profile_job_matches.matched_at (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_job_matches" DROP COLUMN IF EXISTS "matched_at";

-- Drop profile_job_matches.contacted_at (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_job_matches" DROP COLUMN IF EXISTS "contacted_at";

-- Drop profile_job_matches.recruiter_notes (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_job_matches" DROP COLUMN IF EXISTS "recruiter_notes";

-- Drop profile_languages.speaking_level (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_languages" DROP COLUMN IF EXISTS "speaking_level";

-- Drop profile_languages.writing_level (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_languages" DROP COLUMN IF EXISTS "writing_level";

-- Drop profile_languages.reading_level (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profile_languages" DROP COLUMN IF EXISTS "reading_level";

-- Drop profiles.desired_locations (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profiles" DROP COLUMN IF EXISTS "desired_locations";

-- Drop profiles.desired_roles (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profiles" DROP COLUMN IF EXISTS "desired_roles";

-- Drop profiles.expected_salary_max (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profiles" DROP COLUMN IF EXISTS "expected_salary_max";

-- Drop profiles.expected_salary_min (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profiles" DROP COLUMN IF EXISTS "expected_salary_min";

-- Drop profiles.last_activity_date (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "profiles" DROP COLUMN IF EXISTS "last_activity_date";

-- Drop profiles.search_vector (DELETE_SPARSE: 4 rows, 4 distinct)
-- Sample values: '-0198':94C '000':204C,286C '10':15B,103C '100':352C '15':342C '2':285C '200':221C '2013':315C '2014':335C,382C '2016/2019/2022':146C '2017':278C,336C '2020':197C,279C '206':92C '35':233C '365':27B,55B,116C,158C,261C,320C,405C,422C '40':310C '5':203C '555':93C '60':330C '70':246C 'access':32B,180C 'across':288C 'activ':21B,70B,109C,148C,338C,418C 'ad':151C,213C 'administ':280C 'administr':36B,69B,72B,147C,327C,333C,393C,408C 'alert':79B 'analyt':448C 'architect':42B,388C 'arm':51B,186C 'associ':394C 'autom':37B,46B,164C,234C,323C 'aw':429C 'azur':23B,40B,63B,73B,111C,150C,153C,175C,212C,227C,240C,248C,360C,386C,392C,420C,428C,437C,445C,458C 'bachelor':373C 'bash':433C 'basic':430C,465C 'bate':2A,81C 'center':59B,171C,250C,295C,450C 'certif':383C 'certifi':130C,385C,391C,396C,406C 'ci/cd':65B,177C 'cloud':24B,29B,74B,112C,120C,400C,425C 'cloudtech':195C 'cluster':350C 'code':50B,185C,443C 'compet':39B,143C 'complianc':257C,308C 'comptia':410C 'configur':60B,172C,296C 'connect':214C 'control':344C 'core':17B,142C 'cost':231C 'creat':321C 'deep':135C 'deploy':128C,235C,291C,345C 'design':208C 'detect':255C 'devop':64B,176C,241C,438C 'dhcp':456C 'directori':22B,71B,110C,149C,339C,419C 'disast':356C 'distribut':300C 'dns':455C 'domain':18B,343C 'educ':372C 'email':86C 'engin':6A,12B,85C,101C,194C 'english':462C 'enterpris':126C,196C,206C,275C,407C 'enterprise-scal':125C 'environ':30B,121C,207C,283C 'exchang':159C,264C,314C,317C,423C 'experi':13B,190C 'expert':43B,117C,132C,389C,398C,409C 'expertis':136C 'focus':99C 'framework':305C 'french':464C 'gelinda':1A,80C 'gelinda.bates@cloudpro.com':87C 'git':440C 'global':270C 'group':302C 'host':351C 'hybrid':28B,119C,211C 'hyper':167C,347C 'hyper-v':166C,346C 'iaa':154C,228C 'iam':34B,182C 'ident':8B,31B,122C,179C,218C 'implement':210C,247C,301C,355C 'improv':306C 'inc':277C 'includ':263C 'inform':377C 'infrastructur':25B,48B,75B,113C,183C,201C,230C,273C,340C,403C 'key':38B 'languag':461C 'lead':199C 'led':311C 'level':14B 'locat':88C 'log':447C 'machin':354C 'maintain':363C 'manag':33B,57B,61B,76B,123C,173C,181C,219C,259C,293C,297C,304C,337C,371C,452C 'manual':326C 'mcse':44B,133C,399C 'microsoft':4A,10B,26B,54B,83C,98C,115C,129C,139C,152C,157C,192C,200C,260C,272C,384C,390C,395C,404C,414C,421C,427C 'microsoft-focus':97C 'migrat':220C,312C 'monitor':78B,258C,444C,446C 'multipl':289C 'nativ':463C 'network':454C,460C 'offic':319C 'on-premis':222C 'onlin':160C,265C,318C 'oper':451C 'organ':271C 'paa':155C 'patch':370C 'phone':91C 'pipelin':66B,178C 'platform':401C,426C 'polici':303C 'powershel':45B,163C,238C,322C,432C 'premis':224C 'present':198C 'process':236C 'profession':7B,95C,189C 'provis':243C 'python':434C 'recoveri':357C,362C 'reduc':229C,242C,325C 'scale':127C 'sccm':62B,174C,436C 'scienc':375C 'scom':453C 'script':47B,165C,324C,431C 'seamless':217C 'seattl':89C 'secur':156C,249C,307C,411C 'senior':3A,9B,82C,191C 'sentinel':252C 'server':20B,68B,108C,145C,225C,282C,365C,417C 'servic':367C 'sharepoint':161C,266C,424C 'site':290C,361C 'skill':413C 'softwar':299C 'solut':41B,131C,276C,358C,387C,397C 'special':105C 'specialist':274C 'stack':141C 'studio':442C 'summari':96C 'support':284C 'system':5A,11B,35B,58B,77B,84C,100C,170C,193C,294C,332C,449C 'task':328C 'team':162C,268C 'techcorp':334C 'technic':412C 'technolog':140C,378C,415C 'templat':52B,187C 'tenant':56B,262C 'terraform':53B,188C,439C 'threat':254C 'time':244C 'tool':435C 'topolog':215C 'univers':379C 'updat':366C 'use':237C,359C 'user':205C,287C 'v':168C,348C 'virtual':169C,349C,353C,459C 'visual':441C 'vpn':457C 'wa':90C 'washington':381C 'window':19B,67B,107C,144C,281C,331C,364C,416C 'wsus':368C 'year':16B,104C, '-0142':137C '11g':269C,412C '12':15B,73B,145C '12c':32B,90B,186C,406C '12c/19c':158C,236C '12c/19c/21c':422C '19c':33B,91B,187C,271C '2':319C '2012':354C,400C '2015':300C,355C '2018':229C,301C '21c':34B,92B,188C '24/7':362C '25':303C '3':287C '4':246C '415':135C '50':232C '500':329C '555':136C '60':257C '8tb':265C '99.99':179C,250C 'achiev':249C 'across':318C 'administ':302C 'administr':6A,12B,20B,31B,56B,70B,78B,89B,114B,127C,143C,185C,213C,296C,351C,407C,413C 'aix':433C 'alert':369C 'applic':191C 'architectur':63B,121B,220C 'assess':380C 'audit':377C 'autom':276C,366C,386C 'avail':62B,120B,219C,363C 'aw':454C 'bachelor':390C 'backup':51B,109B,208C 'backup/recovery':277C 'bank':353C,358C 'bash':59B,117B,216C,436C 'berkeley':399C 'best':292C 'ca':133C 'california':398C 'capac':323C 'center':321C 'certif':401C,417C 'certifi':403C,409C 'cloud':449C,451C 'cluster':192C,248C 'compet':28B,86B,182C 'complianc':50B,108B,207C,345C 'comput':394C 'concurr':330C 'core':17B,75B,181C,357C 'corp':299C 'creat':381C 'critic':172C 'data':23B,38B,81B,96B,160C,195C,313C,320C,387C,441C 'databas':5A,11B,19B,30B,48B,69B,77B,88B,106B,126C,142C,153C,173C,184C,205C,235C,266C,295C,305C,326C,347C,350C,360C,420C 'dba':225C 'dbas':289C 'design':241C 'develop':47B,105B,204C 'disast':25B,40B,83B,98B,197C,316C 'domain':18B,76B 'downtim':274C 'educ':389C 'electron':307C 'elli':1A,122C 'ellie.larrison@techmail.com':129C 'email':128C 'english':457C 'ensur':343C 'enterpris':151C,372C,446C 'enterprise-level':150C 'experi':13B,71B,148C,222C 'expert':155C,416C 'financi':238C 'fintech':226C 'francisco':132C 'generat':337C 'git':448C 'guard':39B,97B,161C,196C,314C 'harden':349C 'hat':428C 'health':308C 'healthcar':297C 'high':61B,119B,218C 'hipaa':344C 'hour':340C 'ident':8B,66B 'implement':243C,275C,311C,365C 'inc':228C 'infrastructur':452C 'intermedi':460C 'junior':288C 'key':27B,85B 'languag':456C 'larrison':2A,123C 'led':262C 'level':14B,72B,152C 'linux':429C,431C 'linux/unix':54B,112B,211C 'loader':444C 'locat':130C 'manag':24B,82B,149C,169C,231C,356C,373C,447C 'master':410C 'mentor':284C 'migrat':263C 'minut':342C 'mission':171C 'mission-crit':170C 'monitor':367C 'mysql':423C 'nativ':458C 'node':247C 'oci':453C 'ocm':411C 'ocp':405C 'oper':425C 'optim':45B,103B,202C,332C 'oracl':4A,10B,21B,29B,35B,37B,68B,79B,87B,93B,95B,125C,141C,157C,183C,189C,194C,224C,234C,244C,268C,291C,294C,304C,312C,359C,371C,402C,408C,414C,421C,430C,445C,450C 'output':64B 'perform':42B,100B,163C,199C,260C,322C,374C 'perl':438C 'phone':134C 'pl/sql':46B,104B,203C,382C,435C 'plan':324C 'platform':240C 'postgresql':424C 'practic':293C 'present':230C 'procedur':278C,384C 'process':388C 'product':233C 'profession':7B,65B,138C,221C,404C 'proven':165C 'pump':442C 'python':60B,118B,217C,437C 'queri':44B,102B,201C,253C,334C 'rac':36B,94B,159C,193C,245C,415C 'rds':455C 'real':190C 'record':167C,309C 'recoveri':26B,41B,52B,84B,99B,110B,198C,209C,317C 'red':427C 'reduc':252C,335C 'region':352C 'regular':375C 'report':336C 'requir':364C 'respons':254C 'rman':53B,111B,210C,280C,440C 'san':131C 'scienc':392C,395C 'script':58B,116B,215C,283C,434C 'season':140C 'secur':49B,107B,206C,348C,376C 'senior':3A,9B,67B,124C,223C 'shell':57B,115B,214C,282C 'skill':419C 'solari':432C 'solut':227C 'spanish':459C 'sql':333C,443C 'store':383C 'summari':139C 'support':174C,237C,306C 'system':55B,113B,154C,212C,298C,310C,426C 'systemat':259C 'team':285C 'technic':418C 'technolog':22B,80B 'thousand':175C 'time':255C,338C 'tool':439C 'track':166C 'trade':239C 'tune':43B,101B,164C,200C,261C 'univers':396C 'upgrad':327C 'uptim':180C,251C 'use':279C,370C 'user':177C,331C 'vulner':379C 'year':16B,74B,146C 'zero':273C, '-0176':128C '0':500C '000':334C '15':237C '150k':382C '15m':511C '18':323C '180':400C '2':258C '20':341C '200k':514C '2016':372C,421C '2018':310C,373C '2021':230C,311C '2022':522C '2023':534C '250':265C '250k':502C '2m':253C '3':302C '300':70B,170C '300k':320C '310':126C '4':80B,287C '4.5':279C '400':353C '5':333C '500k':251C,273C '50m':330C '555':127C '6':505C '8':18B,140C 'account':378C 'achiev':278C,494C 'across':147C,240C,254C 'ad':479C,485C 'adob':58B,216C,458C 'advertis':43B,201C,477C 'agenc':229C 'airtabl':491C 'analyt':39B,161C,197C,433C,467C,469C 'angel':123C 'annual':274C 'art':414C 'audienc':67B,167C 'averag':261C 'award':526C 'b2b':241C 'b2c':243C 'bachelor':412C 'best':518C 'blueprint':428C 'brand':48B,102B,145C,206C,304C,381C,409C 'brandboost':228C 'budget':277C 'buffer':489C 'build':90B,144C 'built':282C,312C 'busi':471C 'buy':430C 'ca':124C 'california':420C 'campaign':76B,177C,328C,482C,521C 'canva':462C 'capcut':463C 'certif':426C,429C,440C,444C 'channel':351C 'client':239C 'co':371C 'cohes':408C 'combin':246C 'communic':416C 'communiti':31B,84B,154C,189C,291C 'compet':65B,179C 'content':6A,14B,26B,56B,81B,117C,152C,184C,214C,270C,288C,386C,438C,456C 'convers':539C 'coordin':401C 'copi':30B,188C 'copywrit':391C 'core':20B,178C 'creat':325C,384C,507C 'creation':27B,153C,185C,457C 'creativ':59B,131C,217C,405C 'creator':7A,15B,82B,118C,289C 'crisi':51B,87B,209C,294C 'custom':336C 'cut':465C 'daili':385C,397C 'data':107B,134C,268C 'data-driven':106B,133C,267C 'develop':50B,86B,208C,293C,365C 'digit':366C,423C,524C 'disast':300C 'domain':21B 'drive':71B,172C,513C 'driven':108B,135C,269C 'educ':411C 'email':119C 'engag':33B,68B,168C,191C,262C,398C 'english':536C 'enterpris':238C 'experi':16B,143C,223C 'expert':97B,150C 'facebook':44B,202C,377C,427C,451C,478C 'fashion':369C,380C 'featur':527C 'final':464C 'focus':422C 'follow':249C,321C,383C,503C 'gaiq':436C 'generat':329C 'googl':432C,468C 'graphic':29B,187C 'grew':245C,495C 'ground':317C 'grow':66B,166C 'hootsuit':441C,475C,488C 'hubspot':437C 'ident':9B 'implement':105B,358C 'inc':309C 'includ':387C 'increas':260C,346C,396C 'individu':434C 'influenc':34B,156C,192C,338C,345C 'inform':363C 'innov':75B,176C 'insight':476C 'instagram':45B,203C,375C,393C,449C,508C 'key':64B 'languag':535C 'later':490C 'launch':392C 'lead':77B,92B,232C 'led':284C 'level':17B 'linkedin':46B,204C,452C,481C 'listen':100B,360C 'locat':121C 'los':122C 'macro':344C 'major':303C 'manag':32B,52B,85B,88B,104B,155C,190C,210C,272C,292C,295C,307C,337C,374C,480C,483C 'market':35B,57B,193C,215C,367C,425C,439C,443C,525C,532C 'marksberg':2A,113C 'measur':72B,173C 'media':4A,12B,23B,38B,95B,110B,115C,137C,160C,181C,196C,226C,234C,248C,306C,314C,424C,520C,531C 'messag':410C 'meta':470C 'micro':342C 'monday.com':492C 'monitor':54B,212C 'month':324C,506C 'multipl':148C 'nativ':537C 'new':335C 'optim':271C 'paid':41B,199C,275C 'partnership':36B,157C,194C,339C 'phone':125C 'photographi':388C 'photoshop':61B,219C,459C 'pinterest':455C 'plan':25B,183C 'platform':149C,256C,448C 'potenti':298C 'pr':299C,403C 'premier':62B,220C,460C 'presenc':146C,315C 'present':231C 'prevent':297C 'pro':63B,221C,461C,466C 'product':364C 'profession':8B,129C,222C,431C 'protocol':89B,296C 'proven':162C 'qualif':435C 'rate':263C 'record':164C 'reel':509C 'report':40B,198C 'reput':53B,103B,211C 'retail':370C 'roa':281C 'roi':73B,174C 'sale':516C 'sector':244C 'senior':10B,224C 'seo':55B,213C 'skill':446C 'slack':493C 'social':3A,11B,22B,37B,42B,94B,99B,109B,114C,136C,159C,180C,195C,200C,225C,233C,247C,276C,305C,313C,350C,359C,442C,447C,474C,519C,530C 'southern':419C 'spanish':538C 'speaker':528C 'specialist':368C 'sprout':473C 'stori':394C 'strategi':24B,111B,182C,235C,361C,395C 'strategist':5A,13B,116C,138C,227C 'suit':60B,218C,472C 'summari':130C 'team':78B,96B,285C,406C 'technic':445C 'techstartup':308C,496C 'tiktok':47B,205C,327C,450C,484C,498C 'tool':487C 'track':163C 'traffic':348C 'twitter/x':453C 'univers':417C 'video':28B,186C,389C 'view':331C,512C 'viral':326C 'voic':49B,207C 'websit':347C 'won':517C 'world':533C 'x':280C 'year':19B,141C,259C,355C,357C 'year-over-year':354C 'youtub':454C 'zach':1A,112C 'zach.marksberg@socialgenius.com':120C 'zero':318C, '-1997':1843C '-1998':1787C '-1999':1640C '-2002':1549C '-2022':241C '1.8':1081C '12':1106C,1200C '12.000':1452C '12m':1020C '15':44B,561C '18':1102C,1196C '189':1296C '1996':1540C,1842C '1997':1786C '1998':1639C,1726C '200':1368C '2001':1541C,1548C '2002':1462C '2005':966C,1167C,1343C,1463C '2007':1344C '2008':972C,1168C '2010':527C,660C,750C,874C,967C,973C '2012':533C,661C,751C,875C '2015':534C '2016':431C,436C,528C '2020':133C,350C,432C,437C '2021':240C,351C '2022':141C '2m':1458C '30':822C '30min':1529C,1538C '37':1521C,1531C '3x45min':1502C '45min':1517C '46':1100C,1194C '680k':1114C,1208C '70':1097C,1191C '8m':1111C,1205C 'accord':156C,1577C 'action':413C 'activ':584C,921C,1161C,1230C,1484C,1902C 'addit':297C 'adher':167C 'adjust':864C 'administr':1784C 'adob':1229C,1273C,1407C 'adopt':1029C 'ag':970C 'aggreg':945C 'agre':159C,218C 'agreement':81B,950C,1268C 'amount':1109C,1203C 'analysi':105B,113B,440C,807C 'analyz':195C,743C,909C 'annual':595C,897C,1282C 'appli':176C 'applic':227C,635C,745C,1331C,1642C,1700C,1717C 'appropri':412C 'architect':1235C,1643C,1791C 'architectur':84B 'area':312C 'articl':493C 'aspect':572C,590C 'assess':1300C 'assur':1636C 'auction':1424C 'aufbruch':1513C 'autom':100B,226C,301C,1155C 'avail':316C,851C,1708C 'back':1757C 'backend':634C,904C 'backend/frontend':281C 'bahn':1845C,1878C,1906C 'bank':136C,969C,981C,991C,994C,1003C,1353C,1551C,1789C,1808C 'base':14B,504C,1417C 'basel':530C,796C,1544C,1733C 'basi':1339C 'basket':773C 'bea':1409C 'becom':467C 'benefit':604C,786C,965C,1225C 'best':704C,1427C 'bist':1528C 'bku':1867C 'board':420C 'borland':1408C 'brennend':1493C 'budget':1837C,1854C 'build':1362C 'built':1152C 'bulk':955C 'busi':567C,845C,1023C,1261C,1815C,1831C 'byod':861C 'bürokommunik':1865C 'ca':1457C 'calcul':1078C 'capabl':1580C 'captur':256C,341C 'catalogu':1330C,1419C,1434C 'categori':550C,556C,564C,593C,877C,1170C,1176C,1185C 'cdrs':812C 'central':1066C,1400C,1445C,1661C 'cgi':1491C 'chain':614C 'challeng':680C,688C 'chang':463C,538C,1043C,1625C 'charg':1656C 'chief':26B,138C 'chosen':1697C 'cio':1238C 'classif':1885C 'claus':1297C 'cleans':330C 'clear':290C 'client/server':1874C 'client/server-based':1752C 'clm':617C 'cmm':1579C 'co':1182C 'co-l':1181C 'coach':1721C 'coe/2.1':1745C 'collabor':116B 'collect':907C,943C,1809C 'commerzbank':1641C 'committe':1038C 'common':1742C 'communic':117B 'communiti':1833C 'compar':406C 'compet':74B 'compil':1286C,1597C 'complet':1028C,1215C 'complex':347C 'complianc':33B,52B,679C,687C,708C,737C,929C,1052C,1149C,1301C,1347C 'compliance/tech':6A,146C 'compon':1903C 'concept':1686C 'concern':314C 'conclud':1222C 'conclus':516C 'condit':161C,165C,521C,1256C 'connect':809C 'consist':559C 'consolid':653C 'consult':581C 'contact':675C,691C 'contain':770C 'content':489C 'contract':5A,32B,51B,145C,645C,723C,726C,926C,1099C,1130C,1148C,1193C,1289C,1294C,1305C,1329C,1609C,1622C 'contract/s':175C 'contractor':1071C,1088C,1543C 'contractu':80B,158C,317C,348C,1032C,1277C 'coordin':1716C 'core':47B,557C,589C,1772C 'cost':778C,824C,857C,1604C 'cto':29B 'cumbersom':469C 'd':126B 'daili':1783C 'darmstadt':1545C 'das':1505C 'dashboard':1157C 'dass':1525C 'data':56B,103B,106B,108B,112B,206C,212C,267C,298C,640C,643C,810C,1705C,1709C 'databas':646C,927C,1064C 'db':169C,401C,1259C,1288C,1451C 'deal':569C,1013C 'defin':1879C 'deliver':1638C 'demand':756C,764C,948C,1416C 'demand-bas':1415C 'der':1492C,1498C,1508C,1512C 'design':277C,629C,671C,901C,1150C,1658C,1679C,1798C 'desktop':1308C,1749C,1804C,1824C,1841C,1858C 'detail':806C 'deutsch':135C,968C,990C,1352C,1481C,1550C,1674C,1844C,1877C,1905C 'develop':258C,438C,732C,1141C,1718C,1739C 'die':1515C 'director':422C 'disput':1046C 'distil':1818C 'distribut':1447C,1779C 'divis':996C 'division':376C,390C 'document':318C,445C,454C,480C,498C,525C,1033C,1384C,1504C,1771C 'documentari':1520C,1530C,1539C 'domain':48B 'dornbusch':1494C 'draft':840C 'dresdner':1788C,1806C 'drüber':1534C 'du':1526C 'dynam':1293C 'ebranch':1559C 'edit':1489C 'effort':1796C 'einmal':1533C 'elend':1497C 'emea':1179C 'employ':435C 'enabl':284C 'end':1127C,1129C 'end-to-end':1126C 'enforc':1143C 'engin':185C 'ensur':163C,315C,1026C,1051C,1092C 'enterpris':881C,1267C 'entitl':255C,325C 'entitlement/contractual':246C 'environ':1744C,1750C,1875C 'error':1888C 'esourc':619C 'essenti':360C 'establish':1036C,1426C,1869C 'europa':1501C 'evalu':785C,1585C,1599C,1687C,1754C 'execut':119B,1280C 'exist':291C,744C,1287C 'expens':365C,426C,791C 'experi':42B 'expert':721C 'expertis':76B 'extern':1617C,1897C 'extract':20B 'f':1727C 'feasibl':1688C 'feed':637C,1756C 'fernsehen':1482C 'film':1487C 'final':693C,842C 'financ':615C 'financi':39B,63B,65B,352C 'first':690C,1681C,1702C,1873C 'five':1010C 'five-year':1009C 'fix':1107C,1201C 'flag':211C 'focus':30B 'follow':190C 'forecast':408C,818C 'formal':222C,515C 'format':22B 'forward':221C 'framework':441C,1573C 'frankfurt':137C,971C,1546C,1554C,1644C,1792C,1850C 'freelanc':1542C 'freiheit':1516C 'frontend':902C 'function':1586C 'futur':946C 'gap':196C,749C 'gbit':1022C 'geboren':1527C 'generat':230C,484C,1414C,1456C 'germani':1073C,1474C 'gershon':1A 'given':179C 'glanz':1495C 'global':71B,531C,535C,548C,662C,752C,980C,993C,997C,1002C,1172C,1186C,1345C,1349C,1365C,1748C,1764C,1795C,1830C 'good':775C 'govern':57B,59B,67B,109B,355C,541C,545C 'grad':1522C,1532C 'group':554C,669C,759C,889C,895C 'guidanc':699C 'guidelin':1146C 'handl':1444C 'hardwar':1668C 'help':1034C,1892C 'helpdesk':1846C,1870C,1895C 'histor':1503C 'hoffmann':1728C 'hold':393C 'hp':1135C,1227C 'hummingbird':1274C 'ibm':1019C,1340C 'ident':25B 'identif':1882C 'identifi':203C,1089C,1241C 'implement':279C,605C,630C,1253C,1278C,1660C,1800C,1838C,1855C 'import':1244C 'improv':99B,772C 'includ':452C,587C,1279C 'incorpor':18B 'independ':1464C 'inform':848C,913C,934C,1790C,1803C,1810C,1819C,1823C,1840C,1857C 'initi':411C,761C,1069C,1213C,1315C 'input':17B,510C 'instal':1769C 'instruct':23B 'integr':636C,1707C 'interfac':710C 'intern':731C,1061C,1615C 'interwoven':695C 'introduc':1123C 'inventori':925C 'involv':305C 'issu':214C,466C,1397C 'item':295C 'joint':289C 'juden':1499C 'key':73B,502C,1588C 'know':123B 'kpi':302C,658C 'kpis':1041C 'la':1729C 'label':1311C 'larg':448C 'largest':1475C 'law':1055C 'ldap':1712C 'lead':4A,7A,144C,147C,243C,251C,257C,663C,753C,758C,802C,868C 'leadership':36B,85B,88B 'learn':513C 'led':879C,888C,983C,1001C,1065C,1174C,1183C,1276C,1351C 'legaci':1714C 'legal':494C,714C 'let':121B 'level':43B 'lever':853C 'licens':54B,69B,78B,160C,357C,665C,748C,882C,898C,917C,924C,940C,947C,953C,975C,985C,1334C,1356C,1369C,1372C,1396C,1780C 'like':127B 'line':294C,366C 'list':276C,651C 'local':1767C 'locat':1164C 'look':1323C 'lower':777C 'm':1082C 'machin':512C 'maintain':632C,908C,1379C 'mainz':1469C,1547C 'major':685C 'manag':50B,55B,62B,79B,86B,95B,104B,115B,248C,358C,427C,465C,539C,565C,588C,628C,666C,684C,709C,738C,757C,763C,792C,832C,878C,883C,918C,979C,1042C,1096C,1131C,1160C,1171C,1177C,1190C,1317C,1348C,1357C,1370C,1373C,1376C,1391C,1553C,1565C,1576C,1582C,1624C,1647C,1654C,1667C,1691C,1732C,1774C,1781C,1816C,1832C,1849C 'mandatori':1048C 'map':1587C 'master':1295C 'match':520C 'match/no':519C 'materi':1105C,1199C,1472C 'mathwork':1411C 'matter':720C 'matur':1581C 'may':152C 'measur':899C 'member':423C,1736C 'mercuri':1136C 'microsoft':1226C,1272C,1341C,1406C 'mobil':265C,578C,754C,766C 'mode':741C 'model':507C,1570C 'monitor':369C,1040C 'month':394C,415C,1455C 'mose':1510C 'move':735C 'msa':839C 'multipl':453C 'must':170C 'nation':1054C 'negoti':92B,446C,724C,830C,949C,1006C,1083C,1264C,1623C 'network':388C,580C,1907C 'new':201C,223C,1084C,1098C,1192C,1266C,1724C,1802C 'novarti':529C,553C,701C,713C,829C 'object':1262C 'obtain':814C,933C 'offic':28B,140C,1743C 'offlin':1423C 'offshor':1312C 'okay':8B 'onboard':1320C,1695C 'one':359C 'onlin':1421C,1436C 'ontolog':486C 'oper':607C 'optim':97B 'order':293C 'organ':430C,1239C,1358C 'output':13B,233C 'outsourc':583C,1012C,1049C,1894C 'owner':367C 'p.a':1461C 'paragraph':523C 'part':399C,798C,826C,1120C,1556C,1620C,1793C,1861C 'partner':568C,846C,1618C 'per':1429C,1454C 'person':856C 'phrase':503C 'piec':149C 'pilot':1125C 'plan':66B,90B,353C,410C,1834C,1851C,1899C 'poe':286C,331C 'point':194C,673C 'polici':863C,1062C,1381C 'pollatschek':2A 'popul':1699C 'portal':1319C 'portion':835C 'posit':961C 'possibl':747C 'post':1675C 'potenti':311C 'practic':705C 'predict':499C 'prepar':414C 'present':1827C 'prevent':936C 'price':1108C,1202C,1428C 'privat':1807C 'pro':335C 'proactiv':740C 'procedur':608C,1762C,1880C 'process':96B,98B,187C,198C,202C,224C,260C,306C,483C,612C,900C,1132C,1383C,1572C,1693C,1775C 'procur':72B,1173C,1350C,1437C,1449C 'produc':1465C,1470C,1488C 'product':1375C 'product/region':1430C 'profession':24B 'program':884C,891C,1166C 'progress':309C 'project':3A,94B,131C,143C,783C,1321C,1558C,1600C,1646C,1649C,1863C 'proof':244C,253C,323C,1684C 'propos':200C,1596C 'prototyp':1682C 'provid':300C,329C,698C,801C,804C 'provis':247C,349C,477C 'public':1158C,1467C 'publish':1432C 'purchas':181C,269C,292C,952C,1401C 'qualiti':107B,213C,1635C 'quest':1413C 'quick':468C,1884C 'ran':782C,1593C 'rate':1067C,1086C 'recognit':622C 'record':332C,811C 'recur':1887C 'redesign':893C 'reduc':1085C 'reduct':1068C 'reenact':1518C 'refer':320C 'refin':130B 'regul':1057C 'regular':599C,1338C 'relationship':1629C 'relev':266C,346C,501C,914C 'remov':1399C 'replac':1090C,1398C 'report':110B,120B,303C,340C,343C,517C,600C,624C,625C,633C,648C,659C,870C,911C,930C,1156C,1335C 'request':1044C,1453C,1594C 'requir':232C,1024C,1095C,1666C,1811C,1820C 'research':1583C 'resolut':1891C 'resolv':1395C 'respons':542C,1560C,1632C 'ressourc':1665C 'result':962C,1076C,1760C 'revers':184C 'review':205C,372C,395C,402C,418C,1021C,1050C,1612C 'rfi':800C 'risk':1302C,1603C 'roch':1730C 'role':380C,586C,683C,781C,887C,1000C,1189C,1361C,1569C,1678C 'rollout':1719C,1731C,1765C,1848C,1900C 'rule':1144C 'run':1304C 'sam':345C 'sap':616C,697C,880C,916C,957C 'sas':696C 'sauber':1537C 'save':621C,647C,817C,852C,873C,1079C,1113C,1207C,1460C 'saveplan':618C 'scenario':1601C 'schon':1536C 'schön':1524C 'scientif':492C 'script':1486C 'sector':41B 'select':1692C 'self':434C 'self-employ':433C 'senior':46B,1233C,1371C,1390C 'seri':1813C 'serv':667C,717C 'server':1306C 'servic':40B,64B,768C,793C,977C,987C,1017C 'servicenow/sam':334C 'session':396C 'set':385C,526C,597C,1562C,1590C,1703C 'settlement':694C 'sharepoint':650C 'show':307C 'side':457C 'signatur':1332C 'signific':964C,1224C 'singl':672C 'slm':1388C,1441C 'smartsourc':1063C 'softwar':53B,68B,77B,151C,180C,356C,364C,577C,664C,678C,686C,707C,736C,876C,974C,984C,1015C,1101C,1117C,1139C,1169C,1175C,1195C,1211C,1219C,1346C,1355C,1380C,1418C,1446C,1669C,1689C,1778C 'solut':83B,282C,1690C 'sourc':207C,299C,532C,536C,610C,641C,655C,867C,1710C 'space':1118C,1140C,1212C 'specif':1610C 'spend':370C,405C,602C,642C,771C,871C,938C 'staf':1835C,1852C 'stakehold':114B,216C,377C,391C,702C,923C 'standard':102B,459C,606C,657C,1747C 'station':1477C 'statist':506C 'status':474C 'steer':1037C 'strateg':89B,1008C,1218C,1245C,1270C,1325C 'streamlin':481C 'strong':960C 'structur':12B,443C,488C 'sub':563C 'sub-categori':562C 'subject':719C 'suit':1153C 'summari':132C 'supervis':1047C 'suppli':613C 'supplier':1698C 'support':262C,611C,620C,1258C,1263C,1871C 'system':270C,905C,922C,1715C,1753C,1770C,1773C 'systemat':1459C 'target':596C 'task':361C,383C,424C,1785C 'tco':1607C 'team':87B,239C,242C,250C,287C,558C,594C,715C,733C,831C,988C,1004C,1122C,1366C,1389C,1442C,1566C,1725C,1740C,1864C 'tech':35B 'technic':75B,497C 'technolog':27B,49B,139C,1234C,1589C 'telecom':579C,755C,767C,790C 'televis':1468C,1476C 'tem':794C,803C,834C,859C 'templat':727C,1290C 'term':1254C 'termin':1093C 'test':1016C,1759C 'text':444C,495C 'tibco':1342C 'time':1103C,1197C 'today':134C,142C 'took':1619C 'tool':263C,460C,471C,649C,1134C 'top':627C 'track':462C,472C 'train':1364C,1438C 'transact':1216C 'transpar':858C 'trend':403C 'true':941C,1284C 'true-up':1283C 'typic':451C 'und':1496C,1511C,1535C 'understand':182C 'unintend':937C 'unternehmensweit':1866C 'up':942C,1285C 'updat':235C,416C,728C 'upload':271C,337C,1328C 'us':1075C 'usabl':1605C 'use':155C,296C,458C,788C,931C,1298C,1420C,1440C 'user':509C,1653C,1662C,1758C 'user-manag':1652C 'util':210C,511C 'various':639C 'vendor':61B,91B,449C,978C,1159C,1163C,1220C,1246C,1251C,1271C,1318C,1326C,1393C,1403C,1552C,1564C,1575C,1628C,1898C 'verifi':816C 'versa':328C 'vice':327C 'video':1471C 'virtual':1309C 'visibl':172C 'vodaphon':838C 'voip':860C 'warehous':644C 'way':220C 'webmethod':1228C 'well':1059C 'white':1310C 'whole':1672C 'wide':670C,760C,890C,896C 'wie':1523C 'within':37B,1450C,1876C 'work':275C,729C,843C,865C,1231C,1249C,1385C,1734C,1859C 'worklist':236C 'worldwid':1817C 'wrote':1377C,1608C 'wunder':1506C 'wüste':1509C 'year':45B,1011C 'zdf':1479C 'zentral':1651C 'zum':1650C 'zweit':1480C
ALTER TABLE "profiles" DROP COLUMN IF EXISTS "search_vector";

-- Drop profiles.skills_extraction_status (DELETE_CONSTANT: 4 rows, 1 distinct)
-- Sample values: success
ALTER TABLE "profiles" DROP COLUMN IF EXISTS "skills_extraction_status";

-- Drop skill_occurrences.skill_source (DELETE_CONSTANT: 381 rows, 1 distinct)
-- Sample values: posting
ALTER TABLE "skill_occurrences" DROP COLUMN IF EXISTS "skill_source";

-- Drop user_posting_decisions.decision_id (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "user_posting_decisions" DROP COLUMN IF EXISTS "decision_id";

-- Drop user_posting_decisions.cover_letter_draft (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "user_posting_decisions" DROP COLUMN IF EXISTS "cover_letter_draft";

-- Drop user_posting_decisions.no_go_reason (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "user_posting_decisions" DROP COLUMN IF EXISTS "no_go_reason";

-- Drop user_posting_decisions.decision_generated_at (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "user_posting_decisions" DROP COLUMN IF EXISTS "decision_generated_at";

-- Drop user_posting_decisions.decision_workflow_run_id (DELETE_EMPTY: 0 rows, 0 distinct)
-- Sample values: 
ALTER TABLE "user_posting_decisions" DROP COLUMN IF EXISTS "decision_workflow_run_id";

-- Drop workflows.app_scope (DELETE_CONSTANT: 74 rows, 1 distinct)
-- Sample values: talent
ALTER TABLE "workflows" DROP COLUMN IF EXISTS "app_scope";


COMMIT;

-- Verification queries
-- Run these to confirm the columns are gone:

-- Verify conversations
SELECT column_name FROM information_schema.columns WHERE table_name = 'conversations' AND table_schema = 'public' ORDER BY ordinal_position;

-- Verify human_tasks
SELECT column_name FROM information_schema.columns WHERE table_name = 'human_tasks' AND table_schema = 'public' ORDER BY ordinal_position;

-- Verify posting_skills
SELECT column_name FROM information_schema.columns WHERE table_name = 'posting_skills' AND table_schema = 'public' ORDER BY ordinal_position;

-- Verify posting_state_snapshots
SELECT column_name FROM information_schema.columns WHERE table_name = 'posting_state_snapshots' AND table_schema = 'public' ORDER BY ordinal_position;

-- Verify profile_certifications
SELECT column_name FROM information_schema.columns WHERE table_name = 'profile_certifications' AND table_schema = 'public' ORDER BY ordinal_position;

-- Verify profile_education
SELECT column_name FROM information_schema.columns WHERE table_name = 'profile_education' AND table_schema = 'public' ORDER BY ordinal_position;

-- Verify profile_job_matches
SELECT column_name FROM information_schema.columns WHERE table_name = 'profile_job_matches' AND table_schema = 'public' ORDER BY ordinal_position;

-- Verify profile_languages
SELECT column_name FROM information_schema.columns WHERE table_name = 'profile_languages' AND table_schema = 'public' ORDER BY ordinal_position;

-- Verify profiles
SELECT column_name FROM information_schema.columns WHERE table_name = 'profiles' AND table_schema = 'public' ORDER BY ordinal_position;

-- Verify skill_occurrences
SELECT column_name FROM information_schema.columns WHERE table_name = 'skill_occurrences' AND table_schema = 'public' ORDER BY ordinal_position;

-- Verify user_posting_decisions
SELECT column_name FROM information_schema.columns WHERE table_name = 'user_posting_decisions' AND table_schema = 'public' ORDER BY ordinal_position;

-- Verify workflows
SELECT column_name FROM information_schema.columns WHERE table_name = 'workflows' AND table_schema = 'public' ORDER BY ordinal_position;

