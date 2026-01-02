package routines;

public class StringRoutine {

    /**
     * Met en majuscule la chaîne fournie.
     * @param input texte d'entrée
     * @return texte en majuscules
     */
    public static String toUpper(String input) {
        if (input == null) {
            return "";
        }
        return input.toUpperCase();
    }

    /** Concatène prénom et nom. */
    public String formatName(String first, String last) {
        return first + " " + last;
    }
}
