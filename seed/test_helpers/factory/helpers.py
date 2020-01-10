# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import base64
import datetime
import random
from decimal import getcontext, Decimal

getcontext().prec = 7


class DjangoFunctionalFactory:
    @classmethod
    def rand_int(cls, start=0, end=100):
        return random.randint(start, end)

    @classmethod
    def rand_float(cls, start=0, end=100):
        return random.uniform(start, end)

    @classmethod
    def rand_str(cls, length=None):
        # from http://stackoverflow.com/questions/785058/random-strings-in-python-2-6-is-this-ok
        if not length:
            length = cls.rand_int(end=10)
        nbits = length * 6 + 1
        bits = random.getrandbits(nbits)
        uc = '%0x' % bits
        newlen = int(len(uc) / 2) * 2
        ba = bytearray.fromhex(uc[:newlen])
        return base64.urlsafe_b64encode(str(ba))[:length]

    @classmethod
    def rand_phone(cls):
        area = cls.rand_int(start=100, end=999)
        first = cls.rand_int(start=100, end=999)
        last = cls.rand_int(start=1000, end=9999)
        return '%s-%s-%s' % (area, first, last)

    @classmethod
    def rand_street_address(cls):
        s = '%s %s %s' % (cls.rand_int(end=10000), cls.rand_plant_name(), cls.rand_street_suffix())
        return s[:63]

    @classmethod
    def rand_city(cls):
        return '%s%s' % (cls.rand_plant_name(), cls.rand_city_suffix())

    @classmethod
    def rand_bool(cls):
        return cls.rand_int(0, 1) == 0

    @classmethod
    def rand_name(cls):
        return RANDOM_NAME_SOURCE[cls.rand_int(0, len(RANDOM_NAME_SOURCE) - 1)]

    @classmethod
    def rand_plant_name(cls):
        return RANDOM_PLANT_NAME_SOURCE[cls.rand_int(0, len(RANDOM_PLANT_NAME_SOURCE) - 1)]

    @classmethod
    def rand_street_suffix(cls):
        return RANDOM_STREET_SUFFIX_SOURCE[cls.rand_int(0, len(RANDOM_STREET_SUFFIX_SOURCE) - 1)]

    @classmethod
    def rand_city_suffix(cls):
        return RANDOM_CITY_SUFFIX_SOURCE[cls.rand_int(0, len(RANDOM_CITY_SUFFIX_SOURCE) - 1)]

    @classmethod
    def rand_date(cls, start_year=1900, end_year=2011):
        return datetime.date(year=cls.rand_int(start_year, end_year), month=cls.rand_int(1, 12),
                             day=cls.rand_int(1, 28))

    @classmethod
    def rand_currency(cls, start=0, end=100):
        return Decimal(cls.rand_int(start=start * 100, end=end * 100)) / 100

    @classmethod
    def rand_email(cls):
        return '%s@%s' % (cls.rand_name().lower(), cls.rand_domain())

    @classmethod
    def rand_domain(cls):
        return RANDOM_EMAIL_DOMAINS[cls.rand_int(0, len(RANDOM_EMAIL_DOMAINS) - 1)]

    @classmethod
    def valid_test_cc_number(cls):
        return '4242424242424242'

    @classmethod
    def invalid_test_cc_number(cls):
        return '4242424242424241'

    @classmethod
    def test_cc_number(cls, valid=True):
        if valid:
            return cls.valid_test_cc_number()
        else:
            return cls.invalid_test_cc_number()


RANDOM_NAME_SOURCE = [
    "Atricia", "Linda", "Barbara", "Elizabeth", "Jennifer",
    "Maria", "Susan", "Margaret", "Dorothy", "Lisa", "Nancy", "Karen", "Betty",
    "Helen", "Sandra", "Donna", "Carol", "Ruth", "Sharon", "Michelle", "Laura",
    "Sarah", "Kimberly", "Deborah", "Jessica", "Shirley", "Cynthia", "Angela",
    "Melissa", "Brenda", "Amy", "Anna", "Rebecca", "Virginia", "Kathleen",
    "Pamela", "Martha", "Debra", "Amanda", "Stephanie", "Carolyn", "Christine",
    "Marie", "Janet", "Catherine", "Frances", "Ann", "Joyce", "Diane", "Alice",
    "Julie", "Heather", "Teresa", "Doris", "Gloria", "Evelyn", "Jean", "Cheryl",
    "Mildred", "Katherine", "Joan", "Ashley", "Judith", "Rose", "Janice", "Kelly",
    "Nicole", "Judy", "Christina", "Kathy", "Theresa", "Beverly", "Denise",
    "Tammy", "Irene", "Jane", "Lori", "Rachel", "Marilyn", "Andrea", "Kathryn",
    "Louise", "Sara", "Anne", "Jacquelin", "Wanda", "Bonnie", "Julia", "Ruby",
    "Lois", "Tina", "Phyllis", "Norma", "Paula", "Diana", "Annie", "Lillian",
    "Emily", "Robin", "Peggy", "Crystal", "Gladys", "Rita", "Dawn", "Connie",
    "Florence", "Tracy", "Edna", "Tiffany", "Carmen", "Rosa", "Cindy", "Grace",
    "Wendy", "Victoria", "Edith", "Kim", "Sherry", "Sylvia", "Josephine",
    "Thelma", "Shannon", "Sheila", "Ethel", "Ellen", "Elaine", "Marjorie",
    "Carrie", "Charlotte", "Monica", "Esther", "Pauline", "Emma", "Juanita",
    "Anita", "Rhonda", "Hazel", "Amber", "Eva", "Debbie", "April", "Leslie",
    "Clara", "Lucille", "Jamie", "Joanne", "Eleanor", "Valerie", "Danielle",
    "Megan", "Alicia", "Suzanne", "Michele", "Gail", "Bertha", "Darlene",
    "Veronica", "Jill", "Erin", "Geraldine", "Lauren", "Cathy", "Joann",
    "Lorraine", "Lynn", "Sally", "Regina", "Erica", "Beatrice", "Dolores",
    "Bernice", "Audrey", "Yvonne", "Annette", "June", "Samantha", "Marion",
    "Dana", "Stacy", "Ana", "Renee", "Ida", "Vivian", "Roberta", "Holly",
    "Brittany", "Melanie", "Loretta", "Yolanda", "Jeanette", "Laurie", "Katie",
    "Kristen", "Vanessa", "Alma", "Sue", "Elsie", "Beth", "Jeanne", "Vicki",
    "Carla", "Tara", "Rosemary", "Eileen", "Terri", "Gertrude", "Lucy", "Tonya",
    "Ella", "Stacey", "Wilma", "Gina", "Kristin", "Jessie", "Natalie", "Agnes",
    "Vera", "Willie", "Charlene", "Bessie", "Delores", "Melinda", "Pearl", "Arlene",
    "Maureen", "Colleen", "Allison", "Tamara", "Joy", "Georgia", "Constance",
    "Lillie", "Claudia", "Jackie", "Marcia", "Tanya", "Nellie", "Minnie",
    "Marlene", "Heidi", "Glenda", "Lydia", "Viola", "Courtney", "Marian",
    "Stella", "Caroline", "Dora", "Jo", "Vickie", "Mattie", "Terry", "Maxine",
    "Irma", "Mabel", "Marsha", "Myrtle", "Lena", "Christy", "Deanna", "Patsy",
    "Hilda", "Gwendolyn", "Jennie", "Nora", "Margie", "Nina", "Cassandra",
    "Leah", "Penny", "Kay", "Priscilla", "Naomi", "Carole", "Brandy", "Olga",
    "Billie", "Dianne", "Tracey", "Leona", "Jenny", "Felicia", "Sonia", "Miriam",
    "Velma", "Becky", "Bobbie", "Violet", "Kristina", "Toni", "Misty", "Mae",
    "Shelly", "Daisy", "Ramona", "Sherri", "Erika", "Katrina", "Claire",
    "Lindsey", "Lindsay", "Geneva", "Guadalupe", "Belinda", "Margarita", "Sheryl",
    "Cora", "Faye", "Ada", "Natasha", "Sabrina", "Isabel", "Marguerit", "Hattie",
    "Harriet", "Molly", "Cecilia", "Kristi", "Brandi", "Blanche", "Sandy",
    "Rosie", "Joanna", "Iris", "Eunice", "Angie", "Inez", "Lynda", "Madeline",
    "Amelia", "Alberta", "Genevieve", "Monique", "Jodi", "Janie", "Maggie",
    "Kayla", "Sonya", "Jan", "Lee", "Kristine", "Candace", "Fannie", "Maryann", "Opal",
    "Alison", "Yvette", "Melody", "Luz", "Susie", "Olivia", "Flora", "Shelley",
    "Kristy", "Mamie", "Lula", "Lola", "Verna", "Beulah", "Antoinett", "Candice",
    "Juana", "Jeannette", "Pam", "Kelli", "Hannah", "Whitney", "Bridget", "Karla", "Celia",
    "Latoya", "Patty", "Shelia", "Gayle", "Della", "Vicky", "Lynne", "Sheri",
    "Marianne", "Kara", "Jacquelyn", "Erma", "Blanca", "Myra", "Leticia", "Pat",
    "Krista", "Roxanne", "Angelica", "Johnnie", "Robyn", "Francis", "Adrienne",
    "Rosalie", "Alexandra", "Brooke", "Bethany", "Sadie", "Bernadett", "Traci",
    "Jody", "Kendra", "Jasmine", "Nichole", "Rachael", "Chelsea", "Mable",
    "Ernestine", "Muriel", "Marcella", "Elena", "Krystal", "Angelina", "Nadine",
    "Kari", "Estelle", "Dianna", "Paulette", "Lora", "Mona", "Doreen",
    "Rosemarie", "Angel", "Desiree", "Antonia", "Hope", "Ginger", "Janis", "Betsy", "Christie",
    "Freda", "Mercedes", "Meredith", "Lynette", "Teri", "Cristina", "Eula",
    "Leigh", "Meghan", "Sophia", "Eloise", "James", "John", "Robert",
    "Michael", "William", "David", "Richard", "Charles", "Joseph", "Thomas",
    "Christoph", "Daniel", "Paul", "Mark", "Donald", "George", "Kenneth",
    "Steven", "Edward", "Brian", "Ronald", "Anthony", "Kevin", "Jason", "Matthew", "Gary",
    "Timothy", "Jose", "Larry", "Jeffrey", "Frank", "Scott", "Eric", "Stephen",
    "Andrew", "Raymond", "Gregory", "Joshua", "Jerry", "Dennis", "Walter",
    "Patrick", "Peter", "Harold", "Douglas", "Henry", "Carl", "Arthur", "Ryan",
    "Roger", "Joe", "Juan", "Jack", "Albert", "Jonathan", "Justin", "Terry",
    "Gerald", "Keith", "Samuel", "Willie", "Ralph", "Lawrence", "Nicholas", "Roy",
    "Benjamin", "Bruce", "Brandon", "Adam", "Harry", "Fred", "Wayne", "Billy",
    "Steve", "Louis", "Jeremy", "Aaron", "Randy", "Howard", "Eugene", "Carlos",
    "Russell", "Bobby", "Victor", "Martin", "Ernest", "Phillip", "Todd", "Jesse",
    "Craig", "Alan", "Shawn", "Clarence", "Sean", "Philip", "Chris", "Johnny",
    "Earl", "Jimmy", "Antonio", "Danny", "Bryan", "Tony", "Luis", "Mike",
    "Stanley", "Leonard", "Nathan", "Dale", "Manuel", "Rodney", "Curtis",
    "Norman", "Allen", "Marvin", "Vincent", "Glenn", "Jeffery", "Travis", "Jeff", "Chad",
    "Jacob", "Lee", "Melvin", "Alfred", "Kyle", "Francis", "Bradley", "Jesus",
    "Herbert", "Frederick", "Ray", "Joel", "Edwin", "Don", "Eddie", "Ricky",
    "Troy", "Randall", "Barry", "Alexander", "Bernard", "Mario", "Leroy",
    "Francisco", "Marcus", "Micheal", "Theodore", "Clifford", "Miguel", "Oscar",
    "Jay", "Jim", "Tom", "Calvin", "Alex", "Jon", "Ronnie", "Bill", "Lloyd",
    "Tommy", "Leon", "Derek", "Warren", "Darrell", "Jerome", "Floyd", "Leo",
    "Alvin", "Tim", "Wesley", "Gordon", "Dean", "Greg", "Jorge", "Dustin",
    "Pedro", "Derrick", "Dan", "Lewis", "Zachary", "Corey", "Herman", "Maurice", "Vernon",
    "Roberto", "Clyde", "Glen", "Hector", "Shane", "Ricardo", "Sam", "Rick",
    "Lester", "Brent", "Ramon", "Charlie", "Tyler", "Gilbert", "Gene", "Marc",
    "Reginald", "Ruben", "Brett", "Angel", "Nathaniel", "Rafael", "Leslie",
    "Edgar", "Milton", "Raul", "Ben", "Chester", "Cecil", "Duane", "Franklin",
    "Andre", "Elmer", "Brad", "Gabriel", "Ron", "Mitchell", "Roland", "Arnold",
    "Harvey", "Jared", "Adrian", "Karl", "Cory", "Claude", "Erik", "Darryl",
    "Jamie", "Neil", "Jessie", "Christian", "Javier", "Fernando", "Clinton",
    "Ted", "Mathew", "Tyrone", "Darren", "Lonnie", "Lance", "Cody", "Julio", "Kelly",
    "Kurt", "Allan", "Nelson", "Guy", "Clayton", "Hugh", "Max", "Dwayne",
    "Dwight", "Armando", "Felix", "Jimmie", "Everett", "Jordan", "Ian", "Wallace", "Ken",
    "Bob", "Jaime", "Casey", "Alfredo", "Alberto", "Dave", "Ivan", "Johnnie",
    "Sidney", "Byron", "Julian", "Isaac", "Morris", "Clifton", "Willard", "Daryl",
    "Ross", "Virgil", "Andy", "Marshall", "Salvador", "Perry", "Kirk", "Sergio",
    "Marion", "Tracy", "Seth", "Kent", "Terrance", "Rene", "Eduardo", "Terrence",
    "Enrique", "Freddie", "Wade", "Austin", "Stuart", "Fredrick", "Arturo",
    "Alejandro", "Jackie", "Joey", "Nick", "Luther", "Wendell", "Jeremiah",
    "Evan", "Julius", "Dana", "Donnie", "Otis", "Shannon", "Trevor", "Oliver", "Luke",
    "Homer", "Gerard", "Doug", "Kenny", "Hubert", "Angelo", "Shaun", "Lyle",
    "Matt", "Lynn", "Alfonso", "Orlando", "Rex", "Carlton", "Ernesto", "Cameron",
    "Neal", "Pablo", "Lorenzo", "Omar", "Wilbur", "Blake", "Grant", "Horace",
    "Roderick", "Kerry", "Abraham", "Willis", "Rickey", "Jean", "Ira", "Andres",
    "Cesar", "Johnathan", "Malcolm", "Rudolph", "Damon", "Kelvin", "Rudy",
    "Preston", "Alton", "Archie", "Marco", "Wm", "Pete", "Randolph", "Garry",
    "Geoffrey", "Jonathon", "Felipe", "Bennie", "Gerardo", "Ed", "Dominic",
    "Robin", "Loren", "Delbert", "Colin", "Guillermo", "Earnest", "Lucas",
    "Benny", "Noel", "Spencer", "Rodolfo", "Myron", "Edmund", "Garrett", "Salvatore",
    "Cedric", "Lowell", "Gregg", "Sherman", "Wilson", "Devin", "Sylvester", "Kim",
    "Roosevelt", "Israel", "Jermaine", "Forrest", "Wilbert", "Leland", "Simon",
    "Guadalupe", "Clark", "Irving", "Carroll", "Bryant", "Owen", "Rufus",
    "Woodrow", "Sammy", "Kristophe", "Mack", "Levi", "Marcos", "Gustavo", "Jake",
    "Lionel", "Marty", "Taylor", "Ellis", "Dallas", "Gilberto", "Clint",
    "Nicolas", "Laurence", "Ismael", "Orville", "Drew", "Jody", "Ervin", "Dewey", "Al",
    "Wilfred", "Josh", "Hugo", "Ignacio", "Caleb", "Tomas", "Sheldon", "Erick",
    "Frankie", "Stewart", "Doyle", "Darrel", "Rogelio", "Terence", "Santiago",
    "Alonzo", "Elias", "Bert", "Elbert", "Ramiro", "Conrad", "Pat", "Noah",
    "Grady", "Phil", "Cornelius", "Lamar", "Rolando", "Clay", "Percy", "Dexter",
    "Bradford", "Merle", "Darin", "Amos", "Terrell", "Moses", "Irvin", "Saul",
    "Roman", "Darnell", "Randal", "Tommie", "Timmy", "Darrin", "Winston",
    "Brendan", "Toby", "Van", "Abel", "Dominick", "Boyd", "Courtney", "Jan",
    "Emilio", "Elijah", "Cary", "Domingo", "Santos", "Aubrey", "Emmett", "Marlon",
    "Emanuel", "Jerald", "Edmond", "Emil", "Dewayne", "Will", "Otto", "Teddy",
    "Reynaldo", "Bret", "Morgan", "Jess", "Trent", "Humberto", "Emmanuel",
    "Stephan", "Louie", "Vicente", "Lamont", "Stacy", "Garland", "Miles", "Micah",
    "Efrain", "Billie", "Logan", "Heath", "Rodger", "Harley", "Demetrius",
    "Ethan", "Eldon", "Rocky", "Pierre", "Junior", "Freddy", "Eli", "Bryce",
    "Antoine", "Robbie", "Kendall", "Royce", "Sterling", "Mickey", "Chase",
    "Grover", "Elton", "Cleveland", "Dylan", "Chuck", "Damian", "Reuben", "Stan",
    "August", "Leonardo", "Jasper", "Russel", "Erwin", "Benito", "Hans", "Monte",
    "Blaine", "Ernie", "Curt", "Quentin", "Agustin", "Murray", "Jamal", "Devon",
    "Adolfo", "Harrison", "Tyson", "Burton", "Brady", "Elliott", "Wilfredo",
    "Bart", "Jarrod", "Vance", "Denis", "Damien", "Joaquin", "Harlan", "Desmond",
    "Elliot", "Darwin", "Ashley", "Gregorio", "Buddy", "Xavier", "Kermit",
    "Roscoe", "Esteban", "Anton", "Solomon", "Scotty", "Norbert", "Elvin",
    "Williams", "Nolan", "Carey", "Rod", "Quinton", "Hal", "Brain", "Rob",
    "Elwood", "Kendrick", "Darius", "Moises", "Son", "Marlin", "Fidel",
    "Thaddeus", "Cliff", "Marcel", "Ali", "Jackson", "Raphael", "Bryon", "Armand",
    "Alvaro", "Jeffry", "Dane", "Joesph", "Thurman", "Ned", "Sammie", "Rusty",
    "Michel", "Monty", "Rory", "Fabian", "Reggie", "Mason", "Graham", "Kris",
    "Isaiah", "Vaughn", "Gus", "Avery", "Loyd", "Diego", "Alexis", "Adolph",
    "Norris", "Millard", "Rocco", "Gonzalo", "Derick", "Rodrigo", "Gerry",
    "Stacey", "Carmen", "Wiley", "Rigoberto", "Alphonso", "Ty", "Shelby",
    "Rickie", "Noe", "Vern", "Bobbie", "Reed", "Jefferson", "Elvis", "Bernardo",
    "Mauricio", "Hiram", "Donovan", "Basil", "Riley", "Ollie", "Nickolas",
    "Maynard", "Scot", "Vince", "Quincy", "Eddy", "Sebastian", "Federico",
    "Ulysses", "Heriberto", "Donnell", "Cole", "Denny", "Davis", "Gavin", "Emery",
    "Ward", "Romeo", "Jayson", "Dion", "Dante", "Clement", "Coy", "Odell",
    "Maxwell", "Jarvis", "Bruno", "Issac", "Mary", "Dudley", "Brock", "Sanford",
    "Colby", "Carmelo", "Barney", "Nestor", "Hollis", "Stefan", "Donny", "Art",
    "Linwood", "Beau", "Weldon", "Galen", "Isidro", "Truman", "Delmar",
    "Johnathon", "Silas", "Frederic", "Dick", "Kirby", "Irwin", "Cruz", "Merlin",
    "Merrill", "Charley", "Marcelino", "Lane", "Harris", "Cleo", "Carlo",
    "Trenton", "Kurtis", "Hunter", "Aurelio", "Winfred", "Vito", "Collin",
    "Denver", "Carter", "Leonel", "Emory", "Pasquale", "Mohammad", "Mariano",
    "Danial", "Blair", "Landon", "Dirk", "Branden", "Adan", "Numbers", "Clair",
    "Buford", "German", "Bernie", "Wilmer", "Joan", "Emerson", "Zachery",
    "Fletcher", "Jacques", "Errol", "Dalton", "Monroe", "Josue", "Dominique",
    "Edwardo", "Booker", "Wilford", "Sonny", "Shelton", "Carson", "Theron",
    "Raymundo", "Daren", "Tristan", "Houston", "Robby", "Lincoln", "Jame",
    "Genaro", "Gale", "Bennett", "Octavio", "Cornell", "Laverne", "Hung", "Arron",
    "Antony", "Herschel", "Alva", "Giovanni", "Garth", "Cyrus", "Cyril", "Ronny",
    "Stevie", "Lon", "Freeman", "Erin", "Duncan", "Kennith", "Carmine",
    "Augustine", "Young", "Erich", "Chadwick", "Wilburn", "Russ", "Reid", "Myles",
    "Anderson", "Morton", "Jonas", "Forest", "Mitchel", "Mervin", "Zane", "Rich",
    "Jamel", "Lazaro", "Alphonse", "Randell", "Major", "Johnie", "Jarrett",
    "Brooks", "Ariel", "Abdul", "Dusty", "Luciano", "Lindsey", "Tracey",
    "Seymour", "Scottie", "Eugenio", "Mohammed", "Sandy", "Valentin", "Chance", "Arnulfo",
    "Lucien", "Ferdinand", "Thad", "Ezra", "Sydney", "Aldo", "Rubin", "Royal",
    "Mitch", "Earle", "Abe", "Wyatt", "Marquis", "Lanny", "Kareem", "Jamar",
    "Boris", "Isiah", "Emile", "Elmo", "Aron", "Leopoldo", "Everette", "Josef",
    "Gail", "Eloy", "Dorian", "Rodrick", "Reinaldo", "Lucio", "Jerrod", "Weston",
    "Hershel", "Barton", "Parker", "Lemuel", "Lavern", "Burt", "Jules", "Gil",
    "Eliseo", "Ahmad", "Nigel", "Efren", "Antwan", "Alden", "Margarito",
    "Coleman", "Refugio", "Dino", "Osvaldo", "Les", "Deandre", "Normand", "Kieth", "Ivory",
    "Andrea", "Trey", "Norberto", "Napoleon", "Jerold", "Fritz", "Rosendo",
    "Milford", "Sang", "Deon", "Christope", "Alfonzo", "Lyman", "Josiah", "Brant",
    "Wilton", "Rico", "Jamaal", "Dewitt", "Carol", "Brenton", "Yong", "Olin",
    "Foster", "Faustino", "Claudio", "Judson", "Gino", "Edgardo", "Berry", "Alec",
    "Tanner", "Jarred", "Donn", "Trinidad", "Tad", "Shirley", "Prince",
    "Porfirio", "Odis", "Maria", "Lenard", "Chauncey", "Chang", "Tod", "Mel", "Marcelo",
    "Kory", "Augustus", "Keven", "Hilario", "Bud", "Sal", "Rosario", "Orval", "Mauro",
    "Dannie", "Zachariah", "Olen", "Anibal", "Milo", "Jed", "Frances", "Thanh",
    "Dillon", "Amado", "Newton", "Connie", "Lenny", "Tory", "Richie", "Lupe",
    "Horacio", "Brice", "Mohamed", "Delmer", "Dario", "Reyes", "Dee", "Mac",
    "Jonah", "Jerrold", "Robt", "Hank", "Sung", "Rupert", "Rolland", "Kenton",
    "Damion", "Chi", "Antone", "Waldo", "Fredric", "Bradly", "Quinn", "Kip",
    "Burl", "Walker", "Tyree", "Jefferey", "Ahmed", "Willy", "Stanford", "Oren", "Noble",
    "Moshe", "Mikel", "Enoch", "Brendon", "Quintin", "Jamison", "Florencio",
    "Darrick", "Tobias", "Minh", "Hassan", "Giuseppe", "Demarcus", "Cletus",
    "Tyrell", "Lyndon", "Keenan", "Werner", "Theo", "Geraldo", "Lou", "Columbus",
    "Chet", "Bertram", "Markus", "Huey", "Hilton", "Dwain", "Donte", "Tyron",
    "Omer", "Isaias", "Hipolito", "Fermin", "Chung", "Adalberto", "Valentine",
    "Jamey", "Bo", "Barrett", "Whitney", "Teodoro", "Mckinley", "Maximo",
    "Garfield", "Sol", "Raleigh", "Lawerence", "Abram", "Rashad", "King",
    "Emmitt", "Daron", "Chong", "Samual", "Paris", "Otha", "Miquel", "Lacy", "Eusebio",
    "Dong", "Domenic", "Darron", "Buster", "Antonia", "Wilber", "Renato", "Jc",
    "Hoyt", "Haywood", "Ezekiel", "Chas", "Florentin", "Elroy", "Clemente",
    "Arden", "Neville", "Kelley", "Edison", "Deshawn", "Carrol", "Shayne",
    "Nathanial", "Jordon", "Danilo", "Claud", "Val", "Sherwood", "Raymon",
    "Rayford", "Cristobal", "Ambrose", "Titus", "Hyman", "Felton", "Ezequiel",
    "Erasmo", "Stanton", "Lonny", "Len", "Ike", "Milan", "Lino", "Jarod", "Herb",
    "Andreas", "Walton", "Rhett", "Palmer", "Jude", "Douglass", "Cordell",
    "Oswaldo", "Ellsworth", "Virgilio", "Toney", "Nathanael", "Del", "Britt",
    "Benedict", "Mose", "Hong", "Leigh", "Johnson", "Isreal", "Gayle", "Garret",
    "Fausto", "Asa", "Arlen", "Zack", "Warner", "Modesto", "Francesco", "Manual",
    "Jae", "Gaylord", "Gaston", "Filiberto", "Deangelo", "Michale", "Granville",
    "Wes", "Malik", "Zackary", "Tuan", "Nicky", "Eldridge", "Cristophe", "Cortez",
    "Antione", "Malcom", "Long", "Korey", "Jospeh", "Colton", "Waylon", "Von",
    "Hosea", "Shad", "Santo", "Rudolf", "Rolf", "Rey", "Renaldo", "Marcellus",
    "Lucius", "Lesley", "Kristofer", "Boyce", "Benton", "Man", "Kasey", "Jewell",
    "Hayden", "Harland", "Arnoldo", "Rueben", "Leandro", "Kraig", "Jerrell",
    "Jeromy", "Hobert", "Cedrick", "Arlie", "Winford", "Wally", "Patricia",
    "Luigi", "Keneth", "Jacinto", "Graig", "Franklyn", "Edmundo", "Sid", "Porter",
    "Leif", "Lauren", "Jeramy", "Elisha", "Buck", "Willian", "Vincenzo", "Shon",
    "Michal", "Lynwood", "Lindsay", "Jewel", "Jere", "Hai", "Elden", "Dorsey",
    "Darell", "Broderick", "Alonso"
]

RANDOM_PLANT_NAME_SOURCE = [
    "Abelia", "Acacia", "Acer", "Acevedo", "Afra", "Akina",
    "Alaleh", "Alani", "Alder", "Almond", "Althea ", "Alyssum", "Amaranta",
    "Amaryllis", "Anita", "Apricot", "Arousa", "Arusa", "Ash", "Aspen ",
    "Aster", "Astera", "Avishan", "Ayame", "Ayla", "Azalea", "Azargol", "Azargoon",
    "Azarin", "Azhand", "Babuk", "Bahar", "Baharak", "Banafsheh", "Barnacle", "Basil", "Bay",
    "Beech", "Begonia", "Belladonna", "Birch", "Blackberry", "Blossom", "Bluebell ",
    "Booker", "Botan", "Bramble", "Bryony", "Bud", "Burke ", "Buttercup", "Cactus", "Caltha",
    "Camelai", "Camellia", "Carnation", "Cedar", "Cherise", "Cherry", "Cinnamon", "Cliantha",
    "Clover", "Cosmos", "Cyclamen", "Cypress", "Daffodil", "Dahlia",
    "Daisy", "Dandelion", "Daphne", "Dianthe", "Dianthus", "Enola ", "Eranthe", "Fern",
    "Fiorenza", "Fleur", "Fern", "Fiorenza", "Fleur", "Flora", "Freesia", "Fuchsia", "Gardenia",
    "Garland", "Gazania", "Geranium", "Ginger", "Gooseberry", "Gul", "Hawthorne",
    "Hazel", "Holly", "Hollyhock", "Honeysuckle", "Hyacinth", "Iris ", "Ivy", "Jacaranda",
    "Jasmine", "Jessamine", "Juniper", "Kalei", "Lantana", "Laurel", "Leilani", "Licorice ",
    "Lilac", "Lily ", "Lobelia", "Lotus", "Magnolia", "Mallow ", "Mandrake", "Maple",
    "Marguerite", "Marigold", "Mayflower", "Miki", "Mimosa", "Mulberry", "Myrtle ",
    "Nihal", "Olive", "Pansy ", "Patience", "Peach", "Peony", "Peppermint", "Periwinkle",
    "Persimmon", "Petunia", "Pimpernel", "Poppy", "Posey", "Primrose", "Pumpkin",
    "Quince", "Rose", "Rosemary", "Saffron", "Sage", "Shamrock", "Snapdragon",
    "Snowdrop", "Sorrel", "Sunflower", "Sweet Pea", "Tansy ", "Thistle",
    "Tiger-lily", "Truffle", "Tulip", "Verbena ", "Violet", "Willow", "Yasaman", "Yasmin",
    "Yasminah", "Yew", "Zara"
]

RANDOM_STREET_SUFFIX_SOURCE = ['St.', 'Ave.', 'Blvd.', 'Ln.', 'Ct.', 'Pl.', 'Way']

RANDOM_EMAIL_DOMAINS = ['example.com', 'example.net', 'example.org']
# 'gmail.com', 'yahoo.com', 'hotmail.com', 'live.com',
# 'comcast.net', 'qwest.com',

RANDOM_CITY_SUFFIX_SOURCE = ['ville', 'berg', 'ton', 'y', '', 'land']
